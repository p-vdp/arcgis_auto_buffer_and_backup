import os
from datetime import datetime
import requests
import urllib.parse
from generate_access_token import generate_access_token

def update_buffers(token, survey_layer, buffer_layer):
    points = query_layer(token, survey_layer, "1=1")
    try:
        points = points['features']
    except Exception as e:
        return ({500: e}, 500)
    buffers = query_layer(token, buffer_layer, f"1=1")
    try:
        buffers = buffers['features']
    except Exception as e:
        return ({500: e}, 500)
    buffer_ids = {}
    for buffer_ in buffers:
        attr = buffer_['attributes']
        buffer_ids[attr['ORIG_FID']] = [attr['observation_date'], attr['OBJECTID']]
    ok_buffers = []
    new_buffers = []
    for point in points:
        survey_attributes = point['attributes']
        if survey_attributes['objectid'] in buffer_ids:
            ok_buffers.append(buffer_ids[survey_attributes['objectid']][1])
            if buffer_ids[survey_attributes['objectid']][0] == survey_attributes['observation_date']:
                continue
            else:
                delete_feature(token, buffer_layer,buffer_ids[survey_attributes['objectid']][1])
        if (survey_attributes['buffer_ft'] == 0) or (not survey_attributes['buffer_ft']) or (survey_attributes['nest_status'] not in ['active','Active']):
            continue
        attributes = {}        
        for attribute_key in survey_attributes.keys():
            if attribute_key == 'objectid':
                attributes['ORIG_FID'] = survey_attributes['objectid']
            elif survey_attributes[attribute_key] == None:
                continue
            else:
                attributes[attribute_key] = survey_attributes[attribute_key]
        point_x = point['geometry']['x']
        point_y = point['geometry']['y']
        polygon_geo = create_buffer_polygon_geometry(point_x, point_y, attributes['buffer_ft'])
        new_buffer = {
        "attributes": attributes, 
        "geometry": {
            "rings": polygon_geo['rings']
            }
        }
        new_buffers.append(new_buffer)
    all_buffers = query_layer(token, buffer_layer,"1=1")['features']
    for buffer_ in all_buffers:
        if buffer_['attributes']['OBJECTID'] in ok_buffers:
            continue
        else:
            delete_feature(token, buffer_layer, buffer_['attributes']['OBJECTID'])
    if len(new_buffers) > 0:
        add_feature_to_layer(token, buffer_layer, new_buffers)

def create_buffer_polygon_geometry(x,y,distance,f='json',inSr='4326',unit='9002'):
    # inSr means Spatial Reference. 4326 is standard
    # unit 9002 is feet for *obvious* reasons
    url = "https://tasks.arcgisonline.com/ArcGIS/rest/services/Geometry/GeometryServer/buffer"
    payload = f'f={f}&inSr={inSr}&unit={unit}&distances={distance}&geometries=%7B%22geometryType%22%3A%20%22esriGeometryPoint%22%2C%22geometries%22%3A%20%5B%7B%22x%22%3A%20{x}%2C%22y%22%3A%20{y}%7D%5D%7D'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.request("POST", url, headers=headers, data = payload)
    return response.json()['geometries'][0]

def add_feature_to_layer(token, layer, feature_info):
    url = "https://services8.arcgis.com/h6nuPWXA0cJVXvVl/arcgis/rest/services/scr_nest_buffer_2020/FeatureServer/0/addFeatures"
    feat = urllib.parse.quote(str(feature_info))
    payload = 'f=json&token=' + token + '&features=' + feat
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.request("POST", url, headers=headers, data = payload)
    print(response.text.encode('utf8'))
    return response.json()

def delete_feature(token, layer, oid):
    deletes_url = layer + 'applyEdits'
    url = "https://services8.arcgis.com/h6nuPWXA0cJVXvVl/arcgis/rest/services/scr_nest_buffer_2020/FeatureServer/0/applyEdits"
    payload = f'f=json&token={token}&deletes={oid}'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.request("POST", url, headers=headers, data = payload)
    print(response.text.encode('utf8'))
    return response.json()

def query_layer(token, layer, where):
    where = urllib.parse.quote(where)
    query_url = layer + 'query'
    # where = where.escape()
    payload = f'f=json&token={token}&where={where}&outSr=4326&outFields=*'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.request("POST", query_url, headers=headers, data = payload)
    return response.json()

def delete_all_buffers(token, buffer_layer):
    buffers = query_layer(token, buffer_layer, "1=1")['features']
    for buffer_ in buffers:
        OID = buffer_["attributes"]['OBJECTID']
        delete_feature(buffer_layer, OID)
        print(f"Deleting buffer for {OID}")
