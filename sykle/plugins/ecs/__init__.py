"""Manage ECS deployments

Usage:
  syk ecs publish --deployment=<deployment> [--debug]

Options:
  --deployment=<deployment>

Description:
  publish          Build and push images and refresh ecs services.

Example .sykle.json:
  {
    "plugins": {
      "ecs": {
        "production": {
          "cluster": "foo-production",
          "docker_vars": {
            "BACKEND_IMAGE": "*****.amazonaws.com/foo-backend",
            "BUILD_NUMBER": "latest"
          }
        }
        "staging": {
          "cluster": "foo-staging",
          "docker_vars": {
            "BACKEND_IMAGE": "*****.amazonaws.com/foo-backend",
            "BUILD_NUMBER": "latest"
          }
        }
      }
    }
  }
"""
__version__ = '0.1.0'
import os
import logging
from docopt import docopt
from boto3.session import Session
from sykle.plugin_utils import IPlugin


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Plugin(IPlugin):
    """Build docker images, push them to aws ecr, and refresh
    the ecs services that use them.
    """
    NAME = 'ecs'

    def refresh_cluster(self, deploy_config):
        cluster = deploy_config.__dict__.get('cluster')
        session = Session(
            profile_name=os.environ.get('AWS_PROFILE', None),
            region_name=os.environ.get('AWS_REGION', None)
        )
        client = session.client('ecs')
        resp = client.list_services(cluster=cluster)

        for service_arn in resp.get('serviceArns', []):
            logger.info('Updating %s' % service_arn)
            client.update_service(
                cluster=cluster,
                service=service_arn,
                forceNewDeployment=True
            )

    def run(self):
        self.args = docopt(__doc__, version=__version__)
        self.sykle.debug = self.args.get('debug', False)
        deployment = self.args.get('--deployment')
        deploy_config = self.sykle.config.for_deployment(deployment)

        if self.args.get('publish', None):
            self.sykle.dc(
                input=['build'],
                docker_type='prod-build',
                deployment=deployment
            )
            self.sykle.predeploy(deployment)
            self.sykle.push(deployment)
            self.refresh_cluster(deploy_config)
