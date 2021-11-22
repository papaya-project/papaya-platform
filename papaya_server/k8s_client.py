# -*- coding: utf-8 -*-
"""
MIT License

Copyright (C)  PAPAYA EU Project 2021

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

"""
This package provide a function to activate, terminate or obtain information of K8s cluster.
"""
from kubernetes import client, config
from flask import current_app
from typing import List
from papaya_server.exceptions import K8sError
import logging
import threading
import uuid
import yaml
import os

logger = logging.getLogger(__name__)


class OpenPorts:
    """Open Port Manager, allows manage thread safe ports list"""
    def __init__(self, start: int = None, end: int = None):
        self.start = start
        self.end = end
        self.lock = threading.Lock()

        self.ports = [True] * (self.end - self.start + 1)


    def get_available_port(self):

        logger.debug('Waiting for writing lock')
        self.lock.acquire()

        try:
            logger.debug('Acquired a lock')
            ind = next(i for i in range(len(self.ports)) if self.ports[i])
            self.ports[ind] = False
            logger.debug("Acquiring port [{}]".format(self.start + ind))

            return self.start + ind

        except Exception as e:
            logger.error("Error occurred in get_available_port")
            logger.exception(e)
            raise K8sError("No available ports")

        finally:
            logger.debug('Released a lock')
            self.lock.release()


    def release_port(self, port):

        logger.debug('Waiting for a lock')
        self.lock.acquire()
        try:
            logger.debug('Acquired a lock')
            self.ports[port - self.start] = True
            logger.debug("Releasing port [{}]".format(port))
        finally:
            logger.debug('Released a lock')
            self.lock.release()


    def init(self, ports: list = None):
        """
        Load used ports in memory
        :param ports: list of used ports
        :return:
        """
        if ports is not None:
            for p in ports:
                self.ports[p-self.start] = False


class K8s:

    _deployment_api = None
    _service_api = None


    def __init__(self, incluster=False, secret_name='papaya', ports_range: dict = None):

        if self._deployment_api is None or self._service_api is None:

            self.open_ports = OpenPorts(ports_range['start'], ports_range['end'])
            try:
                if incluster:

                    config.load_incluster_config()
                    client.SettingsApi()

                else:
                    # env var KUBECONFIG should be defined
                    config.load_kube_config()

            except Exception as e:
                logging.exception(e)
                logging.error("Error occurred on k8s config loading")

            self._secret_name = secret_name
            self._deployment_api = client.AppsV1Api()
            self._service_api = client.CoreV1Api()
            self._networking_api = client.NetworkingV1beta1Api()


    def create_iam_configmap(self, name, ingress_url, app_port, namespace="papaya"):
        """
        :param name: config map name
        :param ingress_url: application url
        :param app_port: application port
        :param namespace: K8s namespace
        :return:
        """
        upstream_url = 'http://127.0.0.1:' + str(app_port)
        cfgmap_name = name + '-configmap'
        try:

            data = {'discovery-url': os.getenv("IAM_URL", None),
                    'client-id': os.getenv("IAM_CLIENT_ID", None),
                    'client-secret': os.getenv('IAM_CLIENT_SECRET', None),
                    'encryption-key': os.getenv('ENC_KEY', None),
                    'listen': ':3000',
                    'upstream-url': upstream_url,
                    'redirection-url': ingress_url,
                    'ingress.enabled': True,
                    'enable-security-filter': True,
                    'enable-refresh-tokens': True,
                    'enable-session-cookies': False,
                    'server-write-timeout': '600s',
                    'server-read-timeout': '600s',
                    'upstream-response-header-timeout': '600s',
                    'skip-upstream-tls-verify': False,
                    'skip-openid-provider-tls-verify': True,
                    'enable-https-redirection': True,
                    'pass-authorization-header': True,
                    'resources': [{"uri": "/admin*", "groups": ["papaya-admin"]}]
                    }

            body = client.V1ConfigMap(
                    api_version='v1',
                    metadata=client.V1ObjectMeta(
                        namespace=namespace,
                        name=cfgmap_name),

                    data={
                        'keycloak-gatekeeper.conf': yaml.dump(data)
                        })

            current_app.logger.info("Creating application's configuration map [{}] deployment...".format(cfgmap_name))
            self._service_api.create_namespaced_config_map_with_http_info(namespace=namespace, body=body)
            current_app.logger.info("application's configuration map [{}] was created".format(cfgmap_name))

        except Exception as e:
            msg = "Error occurred in create_deployment call"
            logger.error(msg)
            logger.exception(e)

            raise K8sError(msg)


    def create_deployment(self, name, image, namespace, ports, iam=False):
        """
        Create application deployment
        :param name: application name
        :param image: path to image
        :param namespace: cluster namespace in which the service should be deployed
        :param ports: application ports for NodePort service
        :param iam: whether or not to integrate deployment with IAM service
        :return:
        """
        try:
            deployment = self.create_deployment_object(name, image, ports, iam=iam)
            current_app.logger.info("Creating application [{}] deployment...".format(name))
            self._deployment_api.create_namespaced_deployment(body=deployment, namespace=namespace, pretty=True)
            current_app.logger.info("Application [{}] deployment was created".format(name))

        except Exception as e:
            msg = "Error occurred in create_deployment call"
            logger.error(msg)
            logger.exception(e)

            raise K8sError(msg)


    def delete_deployment(self, name, namespace):
        """
        Delete K8s deployment
        :param name: deployment name
        :param namespace: namespace
        :return:
        """
        name = name + "-deployment"

        try:
            self._deployment_api.delete_namespaced_deployment(name=name, namespace=namespace,
                                                              body=client.V1DeleteOptions(
                                                                  propagation_policy='Foreground',
                                                                  grace_period_seconds=5))
        except Exception as e:
            current_app.logger.error("Exception when calling _deployment_api->delete_namespaced_deployment")
            current_app.logger.exception(e)

            raise K8sError("Error occurred in delete_deployment")


    def create_node_port_service(self, name, namespace="default", ports=None):
        """
        create and deploy NodePort service
        :param name: application name
        :param namespace: cluster namespace in which the service should be deployed
        :param ports: TCP ports for NodePort service
        :return: the allocated node_port
        """
        try:

            if ports['target'] is None:
                ports['target'] = ports['source']
                logger.debug("target_port set to be equal to source port")

            service = client.V1Service(
                kind="Service",
                metadata=client.V1ObjectMeta(
                    name=name + "-tcp-service",
                    namespace=namespace),
                spec=client.V1ServiceSpec(type="NodePort",
                                          selector={"app": name})
            )
            service.spec.ports = []

            np = self.open_ports.get_available_port()
            service.spec.ports.append(client.V1ServicePort(name=uuid.uuid4().hex[:6],
                                                           protocol="TCP",
                                                           port=ports['source'],
                                                           target_port=ports['target'],
                                                           node_port=np))

            logger.info("Creating application [{}] ￿NodePort Service...".format(name))
            self._service_api.create_namespaced_service(namespace, body=service, pretty=True)
            logger.info("Application [{}] NodePort service was created".format(name))
            return np

        except Exception as e:
            msg = "Error occurred in create_node_port_service"
            current_app.logger.error(msg)
            current_app.logger.exception(e)

            raise K8sError(msg)


    def delete_service(self, name, namespace):
        """
        Delete application's service
        :param name: application name
        :param namespace:
        :return:
        """
        name = name + "-service"
        try:
            self._service_api.delete_namespaced_service(name=name, namespace=namespace)

        except Exception as e:
            current_app.logger.error("Exception when calling CoreV1Api->delete_service")
            current_app.logger.exception(e)

            raise K8sError("Error occurred in delete_service")


    def delete_ingress(self, name, namespace):

        name = name + "-ingress"
        try:
            self._networking_api.delete_namespaced_ingress(name=name, namespace=namespace)

        except Exception as e:
            current_app.logger.error("Exception when calling CoreV1Api->delete_namespaced_ingress: %s\n" % e)
            current_app.logger.exception(e)
            raise K8sError("Error occurred in delete_ingress")


    def delete_configmap(self, name, namespace):

        cfgmap_name = name + "-configmap"

        try:
            self._service_api.delete_namespaced_config_map(name=cfgmap_name, namespace=namespace)

        except Exception as e:
            current_app.logger.error("Exception when calling CoreV1Api->delete_namespaced_configmap: %s\n" % e)
            current_app.logger.exception(e)
            raise K8sError("Error occurred in delete_configmap")


    def list_pods(self):
        v1 = client.CoreV1Api()
        ret = v1.list_pod_for_all_namespaces(watch=False)
        for i in ret.items:
            print("%s\t%s\t%s" %
                  (i.status.pod_ip, i.metadata.namespace, i.metadata.name))


    def create_deployment_object(self, name: str, image: str, ports: List[int], replicas=1, iam=False):
        """
        :param name: application name
        :param image: image that should run on the server side
        :param ports: application communication ports
        :param replicas: number of replicas to create, default is 1
        :param iam: whether or not to integrate deployment with IAM service
        :return: deployment object
        """
        deployment_name = name + "-deployment"

        containers = []
        volumes = None
        # Configured Pod template container
        service_container = client.V1Container(
            name=name,
            image=image,
            ports=[client.V1ContainerPort(container_port=port) for port in ports])
        containers.append(service_container)

        if iam:
            cfgmap_name = name + "-configmap"
            keycloack_container = client.V1Container(
                name='gatekeeper',
                image='keycloak/keycloak-gatekeeper:7.0.0',
                ports=[client.V1ContainerPort(container_port=3000, name='keycloackport')],
                args=['--config=/etc/keycloak-gatekeeper.conf'],
                volume_mounts=[client.V1VolumeMount(name=cfgmap_name, mount_path='/etc/keycloak-gatekeeper.conf',
                                                    sub_path='keycloak-gatekeeper.conf')])
            volumes = [client.V1Volume(
                name=cfgmap_name, config_map=client.V1ConfigMapVolumeSource(name=cfgmap_name))]
            containers.append(keycloack_container)

        # Create and configure the spec section
        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={"app": name}),
            spec=client.V1PodSpec(containers=containers, volumes=volumes))

        # service_account_name="papaya", automount_service_account_token=True
        # Create the specification of deployment
        spec = client.ExtensionsV1beta1DeploymentSpec(
            replicas=replicas,
            template=template,
            selector={'matchLabels': {'app': name}})
        # Instantiate the deployment object
        deployment = client.ExtensionsV1beta1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=client.V1ObjectMeta(name=deployment_name),
            spec=spec)

        return deployment


    def create_service(self, name=None, namespace=None, port=None, target_port=None):
        """
        Create default service instance
        :param name: application name
        :param namespace: application name space
        :param port: application source port, as defined in Services catalog
        :param target_port: exposed for outside port
        :return:
        """
        try:
            if target_port is None:
                target_port = port
                logger.debug("target_port set to be equal to port")

            body = client.V1Service(
                api_version="v1",
                kind="Service",
                metadata=client.V1ObjectMeta(
                    name=name + "-service"
                ),
                spec=client.V1ServiceSpec(
                    selector={"app": name},
                    ports=[client.V1ServicePort(
                        port=port,
                        target_port=target_port
                    )]
                )
            )
            # Creation of the Deployment in specified namespace
            # (Can replace "default" with a namespace you may have created)
            self._service_api.create_namespaced_service(namespace=namespace, body=body)

        except Exception as e:
            msg = "Error occurred in create_service function"
            logger.error(msg)
            logger.exception(e)

            raise K8sError(msg)


    def create_ingress(self, name, uuid, service_name, service_port, host):

        h = uuid + "." + host
        try:
            body = client.NetworkingV1beta1Ingress(
                api_version="networking.k8s.io/v1beta1",
                kind="Ingress",
                metadata=client.V1ObjectMeta(name=name + "-ingress", annotations={
                    # require https connection
                    "ingress.bluemix.net/redirect-to-https": "true",
                    # increase the package size between the server side component and the client
                    "ingress.bluemix.net/client-max-body-size": "300m",
                    # increase timeout, essential when big packages are sent
                    "ingress.bluemix.net/proxy-connect-timeout": "timeout=600s",
                    "ingress.bluemix.net/proxy-read-timeout": "timeout=600s"
                }),

                spec=client.NetworkingV1beta1IngressSpec(
                    rules=[client.NetworkingV1beta1IngressRule(
                        host=h,
                        http=client.NetworkingV1beta1HTTPIngressRuleValue(
                            paths=[client.NetworkingV1beta1HTTPIngressPath(
                                path="/",
                                backend=client.NetworkingV1beta1IngressBackend(
                                    service_port=service_port,
                                    service_name=service_name
                                )
                            )
                            ]
                        )
                    )
                    ],
                    tls=[client.NetworkingV1beta1IngressTLS(hosts=[h], secret_name=self._secret_name)]
                )
            )

            # Creation of the Deployment in specified namespace
            # (Can replace "default" with a namespace you may have created)
            self._networking_api.create_namespaced_ingress(
                namespace="papaya",
                body=body
            )

        except Exception as e:
            msg = "Error occurred in create_ingress function"
            logger.error(msg)
            logger.exception(e)

            raise K8sError(msg)


    def create_http_service_with_ingress(self, uuid=None, name=None, namespace=None, ports=None, host=None, iam=False):
        """
        Creating and deploying service and connecting this service to ingress service

        :param uuid: uniq identifying string which will be used in the application sub domain
        :param name: application name
        :param namespace: cluster namespace in which the service should be deployed
        :param ports: ports for
        :param host:the ingress base host
        :param iam: whether or not to integrate deployment with IAM service
        :return:
        """
        try:
            target_port = 3000 if iam else ports['target']
            logger.info("Creating application [{}] service...".format(name))
            self.create_service(name=name, namespace=namespace, port=ports['source'], target_port=target_port)
            logger.info("Application [{}] service was created".format(name))

            logger.info("Creating ingress service for application [{}]...".format(name))
            self.create_ingress(name=name, uuid=uuid, service_name=name+'-service',
                                service_port=ports['source'], host=host)
            logger.info("Ingress service for application [{}] was created".format(name))

        except Exception as e:
            msg = "Error occurred in create_http_service_with_ingress"
            logger.error(msg)
            logger.exception(e)
            raise K8sError(msg)


    def terminate_service(self, name=None, namespace=None, type=None, node_port=None, iam=False):
        """
        Delete application
        :param name:  application name
        :param namespace: luster namespace in which the application should be deployed
        :param type: can be one of the following "tcp" "http" or "dual"
        :param node_port: relevant only for TCP or dual communication
        :param iam: whether or not to integrate deployment with IAM service

        :return:
        """
        try:
            logger.info("Deleting application [{}] deployment".format(name))
            self.delete_deployment(name, namespace)
        except:
            logger.info("Wasn't able to delete the deployment service")

        if type == 'dual' or type == 'tcp':
            try:
                logger.info("Deleting application [{}] NodePort service".format(name))
                self.delete_service(name + "-tcp", namespace)

                if node_port:
                    self.open_ports.release_port(node_port)

            except:
                logger.info("Wasn't able to delete the Nodeport service")

        if type == 'dual' or type == 'http':
            try:
                logger.info("Deleting application [{}] service".format(name))
                self.delete_service(name, namespace)
            except:
                logger.info("Wasn't able to delete the service")

        if type == 'dual' or type == 'http':
            try:
                logger.info("Deleting application [{}] ingress".format(name))
                self.delete_ingress(name, namespace)
            except:
                logger.info("Wasn't able to delete ingress service")

        if iam:
            try:
                logger.info("Deleting config map [{}]".format(name))
                self.delete_configmap(name=name, namespace=namespace)
            except:
                logger.info("Wasn't able to delete ingress configmap")

    def deploy_dual_port_application(self, app_name=None, uuid=None, image=None, namespace=None, host=None, ports=None,
                                     iam=False, url=None):
        """
        Create and deploy application that communicates via http and tcp channels
        :param app_name: application name
        :param uuid: application uuid will be used for ingress sub domain
        :param image: path to server side image
        :param namespace: cluster namespace in which the deployment should be deployed
        :param host: the ingress base host
        :param ports: http and tcp source and target port dictionary type of
                {
                    'tcp' : {'source': number, 'target': number},
                    'http': {'source': number, 'target': number}
                }
        :param iam: whether or not to integrate deployment with IAM service
        :param url: ingress url, required for integration with IAM
        :return: application node_port
        """

        try:
            if iam:
                self.create_iam_configmap(namespace=namespace, name=app_name, app_port=ports['http']['source'],
                                          ingress_url=url)
            self.create_deployment(name=app_name, image=image, namespace=namespace,
                                   ports=[ports['http']['source'], ports['tcp']['source']], iam=iam)
            self.create_http_service_with_ingress(uuid=uuid, name=app_name, namespace=namespace, ports=ports['http'],
                                                  host=host, iam=iam)
            return self.create_node_port_service(name=app_name, ports=ports['tcp'], namespace=namespace)

        except K8sError:
            self.terminate_service(name=app_name, namespace=namespace, type="dual", iam=iam)
            raise

        except Exception as e:
            msg = "Error occurred in create_dual_port_application"
            logger.error(msg)
            logger.exception(e)
            self.terminate_service(name=app_name, namespace=namespace, type="dual", iam=iam)
            raise K8sError(msg)


    def deploy_http_application(self, app_name=None, uuid=None, image=None, namespace=None, host=None, ports=None,
                                iam=False, url=None):
        """
        Create and deploy application that communicates via http channel

        :param app_name: application name
        :param uuid: application uuid will be used for ingress sub domain
        :param image: path to server side image
        :param namespace: cluster namespace in which the deployment should be deployed
        :param host: the ingress base host
        :param ports: http and tcp source and target port dictionary type of
                {
                    'http': {'source': number, 'target': number}
                }
        :param iam: whether or not to integrate deployment with IAM service
        :param url: ingress url, required for integration with IAM
        :return:
        """
        try:
            if iam:
                self.create_iam_configmap(namespace=namespace, name=app_name, app_port=ports['http']['source'],
                                          ingress_url=url)

            self.create_deployment(name=app_name, image=image, namespace=namespace,
                                   ports=[ports['http']['source']], iam=iam)
            self.create_http_service_with_ingress(uuid=uuid, name=app_name, namespace=namespace, ports=ports['http'],
                                                  host=host, iam=iam)
        except K8sError:
            self.terminate_service(name=app_name, namespace=namespace, type="http", iam=iam)
            raise

        except Exception as e:
            msg = "Error occurred in create_dual_port_application"
            logger.error(msg)
            logger.exception(e)
            self.terminate_service(name=app_name, namespace=namespace, type="http", iam=iam)
            raise K8sError(msg)


    def deploy_tcp_application(self, app_name=None, uuid=None, image=None, namespace=None, host=None, ports=None):
        """
        Create and deploy application that communicates tcp channels
        :param app_name: application name
        :param uuid: application uuid will be used for ingress sub domain
        :param image: path to server side image
        :param namespace: cluster namespace in which the deployment should be deployed
        :param host: the ingress base host
        :param ports: http and tcp source and target port dictionary type of
                {
                    'tcp' : {'source': number, 'target': number}
                }
        :return: application node_port
        """

        try:
            self.create_deployment(name=app_name, image=image, namespace=namespace,
                                   ports=[ports['http']['source']])

            return self.create_node_port_service(name=app_name, ports=ports['tcp'], namespace=namespace)

        except K8sError:
            self.terminate_service(name=app_name, namespace=namespace, type="http")
            raise

        except Exception as e:
            msg = "Error occurred in create_dual_port_application"
            logger.error(msg)
            logger.exception(e)
            self.terminate_service(name=app_name, namespace=namespace, type="http")
            raise K8sError(msg)
