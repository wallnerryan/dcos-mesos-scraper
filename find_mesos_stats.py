#!/usr/bin/env python

from prometheus_client import start_http_server, Metric, REGISTRY
import requests
requests.packages.urllib3.disable_warnings()
import json
import commands
import sys, os
import time
import logging
logging.basicConfig(level=logging.DEBUG)

class HealthJsonCollector(object):
  def __init__(self, url, svc_u, svc_p):
    self._url = url
    self._svc_u = svc_u
    self._svc_p = svc_p
    self._token = "none"

  def get_token(self):
     logging.info("Getting New Auth Token")
     payload={"uid": self._svc_u, "password": self._svc_p }
     token_r = requests.post('%s/acs/api/v1/auth/login' % self._url, 
                             data=json.dumps(payload), 
                             headers={'Content-Type': 'application/json'},
                             verify=False)
     if token_r.status_code == 200:
       token_json=json.loads(token_r.content)
       self._token = token_json['token']

  def collect(self):

     r = requests.get('%s/mesos/metrics/snapshot' % self._url,
                      headers={'Authorization': 'token='+self._token},
                      verify=False)

     # if failed, refresh token
     if r.status_code == 401:
         logging.info("Failed auth, getting new auth token")
         self.get_token()
         self.collect()
     else:
         mesosmetrics=r.json()
         for mm, val in mesosmetrics.items():
            logging.info(mm)           
            mm_removed_periods = mm.replace("/", "_")
            mm_removed_astr = mm_removed_periods.replace("*", "")
            mm_removed_dashes = mm_removed_astr.replace("-", "_")
            metric = Metric( mm_removed_dashes,'', 'gauge')
            metric.add_sample(mm_removed_dashes, value=val,
                            labels={'name': mm_removed_dashes})
            yield metric
            logging.info("%s:%d" % (mm, val))
          

if __name__ == "__main__":
   if len(sys.argv) > 1:
     if sys.argv[1] == "--help" or sys.argv[1] == "help" or sys.argv[1] == "-help":
       print """
            Make sure MESOS_SVC_U, MESOS_SVC_P, and DCOS_URL are set in the environment
            MESOS_SVC_U: service user used to login to dcos
            MESOS_SVC_P: service user password used to login to dcos
       
       USAGE:
       %s 
       """ % sys.argv[0]
       exit(0)

   uid = os.environ['MESOS_SVC_U']
   uid_p = os.environ['MESOS_SVC_P']
   dcos_url = os.environ['DCOS_URL']

   start_http_server(int(os.environ['PORT0']))
   REGISTRY.register(HealthJsonCollector(dcos_url, uid, uid_p))

   while True: time.sleep(1)
