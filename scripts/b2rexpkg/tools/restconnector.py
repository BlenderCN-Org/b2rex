"""
 Converts xml messages coming from opensim rest into python structs.
"""

import urllib.request, urllib.error
import base64
import binascii
import quopri
import xml.etree.ElementTree as ET

class RestConnector(object):
    def __init__(self):
        self._url = None
    def connect(self, url, username="", password=""):
        """
        Connect to the server.
        """
        self._url = url
        self._username = username
        self._password = password
        self._connect()
    def _connect(self):
        """
        Internal function connecting to the server.
        """
        username = self._username
        password = self._password
        if username and password:
            passman = urllib.request.HTTPPasswordMgrWithDefaultRealm()
            passman.add_password(None, self._url, username, password)
            self.authhandler = urllib.request.HTTPBasicAuthHandler(passman)
            self.passman = passman
            self.opener = urllib.request.build_opener(self.authhandler)
        else:
            self.opener = urllib.request.build_opener()
    def httpGet(self, relative_url):
        """
        Get an url using GET method.
        """
        self._connect()
        print(self._url + relative_url)
        req = urllib.request.Request(self._url + relative_url)
        req = self.opener.open(req)
        return req.read()
    def httpXmlGet(self, relative_url):
        """
        Get an url using GET method and decode incoming xml into an ET.
        """
        data = self.httpGet(relative_url)
        return ET.fromstring(data)
    def httpObjGet(self, relative_url, subst=""):
        """
        Get an url using GET method and decode incoming xml into a dict.
        """
        xmldata = self.httpXmlGet(relative_url)
        return self.mapToDict(xmldata, subst)
    def mapToDict(self, xmldata, subst=""):
        """
        Map the given xml to a dictionary.
        """
        #print(xmldata.text)
        obj = {}
        for prop in xmldata.getchildren():
            obj[prop.tag[len(subst):]] = prop.text
        for prop, val in xmldata.items():
            obj[prop] = val
        if xmldata.text:
#            pass
           # if len(xmldata.text) < 1000:
           #     print(len(xmldata.text))
           #     print(region_id)
      
            #print(region_id)
            #scenedata = con._con.ogrescene_list({"RegionID":region_id})
#            print(xmldata.text)
            #obj["data"] = binascii.a2b_base64(xmldata.text)
#                pp = quopri.decodestring(xmldata.text)
  
            obj["data"] = base64.decodestring(bytes(xmldata.text, "ascii"))
            #obj["data"] = base64.b64decode(xmldata.text)
        return obj


