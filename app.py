from flask import Flask, render_template, url_for, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import configparser
import os
from gis_functions import update_buffers, query_layer
from generate_access_token import generate_access_token
import requests
import urllib.parse
import gspread

app = Flask(__name__)
app.secret_key = "tnc205app"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tnc205.db'
db = SQLAlchemy(app)
config = configparser.ConfigParser()
config.read('static/utils/carriers.config')

class BirdNest(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    nest_id = db.Column(db.String(256))
    species = db.Column(db.String(256), nullable=False)
    buffer_ft = db.Column(db.Integer, nullable=False)
    nest_status = db.Column(db.String(256), nullable=True)
    nest_activity = db.Column(db.String(256), nullable=True)
    eggs = db.Column(db.Integer)
    chicks = db.Column(db.Integer)
    fenced_or_marked = db.Column(db.String(1024), nullable=True)
    anticipated_fledge_date = db.Column(db.DateTime)
    observation_date = db.Column(db.DateTime, default = datetime.now())
    project_area = db.Column(db.String(256), nullable=True)
    geopoint = db.Column(db.String(2048), nullable=True)
    image = db.Column(db.String(256), nullable=True)
    audio = db.Column(db.String(256), nullable=True)
    weather_conditions = db.Column(db.String(512), nullable=True)
    nest_description = db.Column(db.String(512), nullable=True)
    biologists_observations = db.Column(db.String(512), nullable=True)
    disturbance_notes = db.Column(db.String(512), nullable=True)
    device_id = db.Column(db.String(128), nullable=True)
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)
    accuracy = db.Column(db.String(128))
    CreationDate = db.Column(db.DateTime)
    EditDate = db.Column(db.DateTime)
    Creator = db.Column(db.String(256))
    Editor = db.Column(db.String(256))

    def __repr__(self):
        return f'Report #{self.id}'

gc = gspread.service_account(filename = './config/tnc205-auto-upload-a97fe4207469.json')

@app.route('/run')
def run_functions():
    token = generate_access_token()
    survey_layer = "https://services8.arcgis.com/h6nuPWXA0cJVXvVl/arcgis/rest/services/service_b73efc4d3c0f412f951a910e4aed1558/FeatureServer/0/"
    buffer_layer = "https://services8.arcgis.com/h6nuPWXA0cJVXvVl/arcgis/rest/services/scr_nest_buffer_2020/FeatureServer/0/"           
    
    try:
        update_buffers(token, survey_layer, buffer_layer)
    except Exception as e:
        return ({500: "Unable to update buffers: "+e}, 500)
    survey_features = query_layer(token, survey_layer, "1=1")
    if not survey_features['features']:
        return ({404: "No survey features found"}, 404)
    else:
        survey_features = survey_features['features']
    sh = gc.open("TNC205AutoUpload").sheet1
    num_rows = len(sh.col_values(1))
    for feature in survey_features:
        attr = feature['attributes']
        geo = feature['geometry']
        e_date = attr['EditDate']
        if type(e_date) == int:
            e_date = datetime.fromtimestamp(e_date/1000)
        search_result = BirdNest.query.filter(BirdNest.id == attr['objectid'], BirdNest.EditDate == e_date).first()
        if search_result:
            continue
        species = attr['species']
        if species == "other":
            species = attr['species_other']
        
        nest_status = attr['nest_status']
        if nest_status == 'other':
            nest_status = attr['nest_status_other']
        
        nest_activity = attr['nest_activity']
        if nest_activity == 'other':
            nest_activity = attr['nest_activity_other']

        # Dates
        o_date = attr['observation_date']
        if type(o_date) == int:
            o_date = datetime.fromtimestamp(o_date/1000)

        c_date = attr['CreationDate']
        if type(c_date) == int:
            c_date = datetime.fromtimestamp(c_date/1000)
            

        a_date = attr['anticipated_fledge_date']
        if type(a_date) == int:
            a_date = datetime.fromtimestamp(a_date/1000)
        new_nest_entry = BirdNest(
            id = attr['objectid'],
            nest_id = attr['nest_id'],
            species = species,
            buffer_ft = attr['buffer_ft'],
            nest_status = nest_status,
            nest_activity = nest_activity,
            eggs = attr['eggs'],
            chicks = attr['chicks'],
            fenced_or_marked = attr['fenced_or_marked'],
            anticipated_fledge_date = a_date,
            observation_date = o_date,
            project_area = attr['project_area'],
            geopoint = str(geo),
            image = '',
            audio = '',
            weather_conditions = attr['weather_conditions'],
            nest_description = attr['nest_description'],
            biologists_observations = attr['biologists_obervations'], # note the typo...
            disturbance_notes = attr['disturbance_notes'],
            device_id = attr['device_id'],
            lat = geo['y'],
            lon = geo['x'],
            accuracy = attr['accuracy'],
            CreationDate = c_date,
            EditDate = e_date,
            Creator = attr['Creator'],
            Editor = attr['Editor'],
        )
        db.session.add(new_nest_entry)
        db.session.commit()

        # Now fill for GSheets
        vals = []
        vals.append(attr['objectid'])
        vals.append(attr['nest_id'])
        vals.append(species)
        vals.append(attr['buffer_ft'])
        vals.append(nest_status)
        vals.append(nest_activity)
        vals.append(attr['eggs'])
        vals.append(attr['chicks'])
        vals.append(attr['fenced_or_marked'])
        if a_date:
            vals.append(a_date.strftime("%m/%d/%Y, %H:%M"))
        if o_date:
            vals.append(o_date.strftime("%m/%d/%Y, %H:%M"))
        vals.append(attr['project_area'])
        vals.append(str(geo))
        vals.append('')
        vals.append('')
        vals.append(attr['weather_conditions'])
        vals.append(attr['nest_description'])
        vals.append(attr['biologists_obervations']) # note the typo in ob/s/ervations...)
        vals.append(attr['disturbance_notes'])
        vals.append(attr['device_id'])
        vals.append(geo['y'])
        vals.append(geo['x'])
        vals.append(attr['accuracy'])
        if c_date:
            vals.append(c_date.strftime("%m/%d/%Y, %H:%M"))
        if e_date:
            vals.append(e_date.strftime("%m/%d/%Y, %H:%M"))
        vals.append(attr['Creator'])
        vals.append(attr['Editor'])
        
        num_rows += 1
        sh.update(f"A{num_rows}:AA{num_rows}", [vals])

if __name__ == "__main__":
    app.run(debug=False)