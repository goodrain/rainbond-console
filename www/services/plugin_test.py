# -*- coding: utf8 -*-

import sys
sys.path.append("/Users/pujielan/Documents/code/goodrain/goodrain_web")
from www.models import ConstKey
from www.services import PluginService

buildConf = {
  ConstKey.DOWNSTREAM_PORT:[
    {
      "dest_service1":{
        "5000":[
          {
            "attr_name": "domain",
            "attr_type": "string",
            "attr_value": "www.dest_service1_5000.com",
            "attr_default_value": "www.baidu1_5000.com",
            "is_change": True
          },
          {
            "attr_name": "circuit",
            "attr_type": "int",
            "attr_value": "2048",
            "attr_default_value": "1024",
            "is_change": True
          },
          {
            "attr_name": "prefix",
            "attr_type": "string",
            "attr_value": "/",
            "attr_default_value": "/",
            "is_change": True
          }
        ],
        "6000":[
          {
            "attr_name": "domain",
            "attr_type": "string",
            "attr_value": "www.dest_service1_6000.com",
            "attr_default_value": "www.baidu1_6000.com",
            "is_change": True
          },
          {
            "attr_name": "circuit",
            "attr_type": "int",
            "attr_value": "2048",
            "attr_default_value": "1024",
            "is_change": True
          },
          {
            "attr_name": "prefix",
            "attr_type": "string",
            "attr_value": "/",
            "attr_default_value": "/",
            "is_change": True
          }
        ]
      },
      "dest_service2":{
        "5000":[
          {
            "attr_name": "domain",
            "attr_type": "string",
            "attr_value": "www.dest_service2_5000.com",
            "attr_default_value": "www.baidu2_5000.com",
            "is_change": True
          },
          {
            "attr_name": "circuit",
            "attr_type": "int",
            "attr_value": "2048",
            "attr_default_value": "1024",
            "is_change": True
          },
          {
            "attr_name": "prefix",
            "attr_type": "string",
            "attr_value": "/",
            "attr_default_value": "/",
            "is_change": True
          }
        ],
        "6000":[
          {
            "attr_name": "domain",
            "attr_type": "string",
            "attr_value": "www.dest_service2_6000.com",
            "attr_default_value": "www.baidu2_6000.com",
            "is_change": True
          },
          {
            "attr_name": "circuit",
            "attr_type": "int",
            "attr_value": "2048",
            "attr_default_value": "1024",
            "is_change": True
          },
          {
            "attr_name": "prefix",
            "attr_type": "string",
            "attr_value": "/",
            "attr_default_value": "/",
            "is_change": True
          }
        ]
      }
    }
  ],
  ConstKey.UPSTREAM_PORT:{
    "5000":[
        {
          "attr_name": "domain",
          "attr_type": "string",
          "attr_value": "www.service_5000.com",
          "attr_default_value": "www.baidu_5000.com",
          "is_change": True
        },
        {
          "attr_name": "circuit",
          "attr_type": "int",
          "attr_value": "2048",
          "attr_default_value": "1024",
          "is_change": True
        },
        {
          "attr_name": "prefix",
          "attr_type": "string",
          "attr_value": "/",
          "attr_default_value": "/",
          "is_change": True
        }
      ],
      "6000":[
        {
          "attr_name": "domain",
          "attr_type": "string",
          "attr_value": "www.service_6000.com",
          "attr_default_value": "www.baidu_6000.com",
          "is_change": True
        },
        {
          "attr_name": "circuit",
          "attr_type": "int",
          "attr_value": "2048",
          "attr_default_value": "1024",
          "is_change": True
        },
        {
          "attr_name": "prefix",
          "attr_type": "string",
          "attr_value": "/",
          "attr_default_value": "/",
          "is_change": True
        }
      ]
  },
  ConstKey.AUTO_JNJECTION:[
    {
      "attr_name": "domain_injection",
      "attr_type": "string",
      "attr_value": "www.service_6000.com",
      "attr_default_value": "www.baidu_6000.com",
      "is_change": True
    },
    {
      "attr_name": "circuit_injection",
      "attr_type": "int",
      "attr_value": "2048",
      "attr_default_value": "1024",
      "is_change": True
    },
    {
      "attr_name": "prefix_injection",
      "attr_type": "string",
      "attr_value": "/",
      "attr_default_value": "/",
      "is_change": True
    }    
  ],
  ConstKey.AUTO_ENV:[
    {
      "attr_name": "domain",
      "attr_type": "string",
      "attr_value": "www.service_6000.com",
      "attr_default_value": "www.baidu_6000.com",
      "is_change": True
    },
    {
      "attr_name": "circuit",
      "attr_type": "int",
      "attr_value": "2048",
      "attr_default_value": "1024",
      "is_change": True
    },
    {
      "attr_name": "prefix",
      "attr_type": "string",
      "attr_value": "/",
      "attr_default_value": "/",
      "is_change": True
    }
  ]
}

if __name__ == '__main__':
    ps = PluginService()
    service_id = "test_servicesID"
    service_alias = "grmain123"
    plugin_id="testtesttesttest123123"
    build_version="buildversion123123"
    configMaps = buildConf
    _complex, normal, rc = ps.postStoreAttrs(service_id, service_alias, plugin_id, build_version, configMaps)
    print _complex
    print normal
    print rc 

