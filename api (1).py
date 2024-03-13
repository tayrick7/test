####################### API #########################################
# 1. Authentication 
#     a) SignUp - Done
#     b) Login - Done
#     c) Reset Password - Not yet implemented

# 2. Data management - Done by Yuxuan
#     a) Upload data
#     b) List datasets
#     c) Preview dataset
#     d) Download dataset
# 3. Pipeline
#     a) list dataset
#     a) Create pipeline
#     b) List pipelines
#     c) Select pipeline template
#     d) run pipeline
# 4. Anomaly detection
#     a) Identified anomalies
#     b) Action on anomalies
#     c) View Anomaly logs
# 5. ML Model
#     a) List models
#     b) select models
#     c) Model performance Evaluation
#####################################################################
import pandas as pd
from flask import Flask, request, jsonify, Response, make_response
from flask_restx import Api, Resource, fields, reqparse

import requests
import json
from flask import send_file
from datetime import datetime
from sqlalchemy import create_engine,Table, Column, Integer, String, MetaData, select, update,text, ForeignKey, DateTime


app = Flask(__name__)
# app.run(host="0.0.0.0", port=8000,debug=True)
api = Api(app, version='1.0', title='Anomaly Detection API')

##db setup
#change the password if you using different one
DATABASE_URL = 'mysql+pymysql://root:mysql123@localhost:3306/gpteadb'
engine = create_engine(DATABASE_URL)
metadata = MetaData()

credentials = Table('credentials', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('email', String(255), unique=True, nullable=False), 
    Column('password', String(255), nullable=False),
    Column('created_timestamp', DateTime, nullable=False, default=datetime.utcnow)
)

user_log = Table('user_log', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('email', String(255), unique=False, nullable=False), 
    Column('log_timestamp', DateTime, nullable=False, default=datetime.utcnow)
)

pipeline = Table('pipeline', metadata,
    Column('pipeline_id', Integer, primary_key=True, autoincrement=True),
    Column('pipeline_name', String(255), unique=True, nullable=False), 
    Column('email', String(255), nullable=False), 
    Column('created_timestamp', DateTime, nullable=False, default=datetime.utcnow)
)
model = Table('model', metadata,
    Column('model_id', Integer, primary_key=True, autoincrement=True),
    Column('model_name', String(255), unique=True, nullable=False), 
    Column('created_timestamp', DateTime, nullable=False, default=datetime.utcnow)
)

pipeline_model = Table('pipeline_model', metadata,
    Column('pipeline_model_id', Integer, primary_key=True, autoincrement=True),  # Unique identifier for each association
    Column('pipeline_name', String(255), ForeignKey('pipeline.pipeline_name'), nullable=False),
    Column('model_name', String(255), ForeignKey('model.model_name'), nullable=False),
    Column('created_timestamp', DateTime, nullable=False, default=datetime.utcnow)
)
anomaly_log = Table('anomaly_log', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('dataset', String(255), nullable=False),
    Column('pipeline_name', String(255), ForeignKey('pipeline.pipeline_name'), nullable=False),
    Column('model_name', String(255), ForeignKey('model.model_name'), nullable=False),
    Column('email', String(255)),
    Column('timestamp', DateTime),
    Column('anomaly_type', String(255)),
    Column('number_of_instances', Integer),
    Column('user_action', String(255)),
    Column('created_timestamp', DateTime, default=datetime.utcnow)
)
metadata.create_all(engine, checkfirst=True)



Auth_namespace = api.namespace('Authentication', description='User Authentication description')
user_model = api.model('user_model', {
    'email': fields.String(required=True, description="The user's email"),
    'password': fields.String(required=True, description='The user password')
})


### ML Model
model_namespace = api.namespace('Model', description='Machine Learning models')
ML_model= api.model('ML_model', {
    'model': fields.String(required=True, description='model name')
})

### pipeline 
pipeline_namespace = api.namespace('Pipeline', description='pipeline template')
Pipeline_model= api.model('Pipeline_model', {
    'pipeline': fields.String(required=True, description='pipeline name'),
    'email': fields.String(required=True, description='User email')
})

### pipeline 
pipeline_model_namespace = api.namespace('Pipeline_Model', description='pipeline template')
Pipeline_model_field = api.model('PipelineModel', {
    'pipeline': fields.String(required=True, description='The name of the pipeline'),
    'models': fields.List(fields.String, description='A list of selected models')
})


### pipeline 
anomaly_namespace = api.namespace('Anomaly', description='Anomaly log')
anomaly_detail = anomaly_namespace.model('anomaly_detail', {
    'model_name': fields.String(required=True, description='ML model'),
    'anomaly_type': fields.String(required=True, description='anomaly type'),
    'number_of_instances': fields.Integer(required=True, description='Number of instances'),
    'user_action': fields.String(required=True, description='User action')
})

anomaly_model_field = anomaly_namespace.model('anomaly_model', {
    'dataset': fields.String(required=True, description='The name of the dataset'),
    'pipeline': fields.String(required=True, description='The name of the pipeline'),
    'email': fields.String(required=True, description='User email'),
    # 'timestamp': fields.DateTime(required=True, description='Date and time of the anomaly'),
    'anomaly': fields.List(fields.Nested(anomaly_detail), description='A list of anomalies'),
})

### Change using email and store info into db for both signup and login
@Auth_namespace.route('/signup')
class signup(Resource):
    @Auth_namespace.expect(user_model)
    def post(self):

        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        created_timestamp = datetime.utcnow()
        if not email or not password:
            return {"error": "Email and password are required"}, 400
        
        query = text("SELECT * FROM credentials WHERE email = :email")
        with engine.connect() as conn:
            result = conn.execute(query, {"email": email}).fetchone()
            if result:
                 return {"error": "Email is already taken, choose different"}, 401
            else:
                query = text("INSERT INTO credentials (email, password, created_timestamp) VALUES (:email, :password, :created_timestamp)")
                result = conn.execute(query, {"email": email, "password": password, "created_timestamp": created_timestamp})
                #conn.commit()
                return {'message': 'User signed up successfully'}, 201
            
##################
###### Nice to have - 1) Password strength check

@Auth_namespace.route('/login')
class login(Resource):
    @Auth_namespace.expect(user_model)
    def post(self):

        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        log_timestamp = datetime.utcnow()
        query = text("SELECT * FROM credentials WHERE email = :email and password = :password")
        with engine.connect() as conn:
            result = conn.execute(query, {"email": email, "password": password}).fetchone()

            if result:
                 query = text("INSERT INTO user_log (email, log_timestamp) VALUES (:email, :log_timestamp)")
                 result = conn.execute(query, {"email": email,"log_timestamp": log_timestamp})
                 #conn.commit()
                 return {"success": "Logged in successfully"}, 200
            else:
                return {"error": "Email or password is wrong"}, 400
##################
###### Nice to have - 1) Lock user attempts for logging in after 3 wrong attempts

        
@model_namespace.route('')
class Model(Resource):
    @model_namespace.expect(ML_model)
    def post(self):
        data = request.get_json()
        model_name = data.get('model')
        created_timestamp = datetime.utcnow()
        
        if not model_name:
            return {"error": "model is required"}, 400
        
        select_query = text("SELECT * FROM model WHERE model_name = :model")
        insert_query = text("INSERT INTO model (model_name, created_timestamp) VALUES (:model, :created_timestamp)")

        with engine.connect() as conn:
            result = pd.read_sql_query(select_query, conn, params={"model": model_name})
            if not result.empty:
                return {"error": "Model already exists"}, 400
            else:
                conn.execute(insert_query, {"model": model_name, "created_timestamp": created_timestamp})
                #conn.commit()
                return {'message': 'Model added successfully'}, 201

    def get(self):
        select_query = "SELECT * FROM model"

        with engine.connect() as conn:
            result = pd.read_sql_query(select_query, conn)
            if result.empty:
                return {"error": "No model found"}, 400
            result['created_timestamp'] = result['created_timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            models_list = result.to_dict(orient='records')
            return {'message': 'Listed all models', 'model_list': models_list}, 200
        

       
@pipeline_namespace.route('')
class Pipeline(Resource):
    @pipeline_namespace.expect(Pipeline_model)
    def post(self):
        data = request.get_json()
        pipeline_name = data.get('pipeline')
        email = data.get('email')
        created_timestamp = datetime.utcnow()

        if not pipeline_name:
            return {"error": "pipeline is required"}, 400
        

        select_query = text("SELECT * FROM pipeline WHERE pipeline_name = :pipeline_name")
        insert_query = text("INSERT INTO pipeline (pipeline_name,email, created_timestamp) VALUES (:pipeline_name, :email, :created_timestamp)")

        with engine.connect() as conn:
            result = pd.read_sql_query(select_query, conn, params={"pipeline_name": pipeline_name})
            if not result.empty:
                return {"error": "Pipeline already exists"}, 400
            else:
                conn.execute(insert_query, {"pipeline_name": pipeline_name, "email": email, "created_timestamp": created_timestamp})
                #conn.commit()
                return {'message': 'Model added successfully'}, 201

    def get(self):
        select_query = "SELECT * FROM pipeline"

        with engine.connect() as conn:
            result = pd.read_sql_query(select_query, conn)
            if result.empty:
                return {"error": "No pipeline association found"}, 400
            result['created_timestamp'] = result['created_timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            pipeline_list = result.to_dict(orient='records')
            return {'message': 'Listed all pipelines', 'pipeline_list': pipeline_list}, 200
        
### Nice to have  - Delete template


@pipeline_model_namespace.route('')
class Pipeline_Model(Resource):
    @pipeline_model_namespace.expect(Pipeline_model_field)
    def post(self):
        data = request.get_json()
        pipeline_name = data.get('pipeline')
        models = data.get('models')
        created_timestamp = datetime.utcnow()

        if not pipeline_name:
            return {"error": "pipeline is required"}, 400
        
        select_pipeline_query = text("SELECT * FROM pipeline WHERE pipeline_name = :pipeline_name")
        select_model_query = text("SELECT * FROM model WHERE model_name = :model_name")
        select_pipeline_model_query = text("SELECT * FROM pipeline_model WHERE model_name = :model_name and pipeline_name = :pipeline_name")
        insert_query = text("INSERT INTO pipeline_model (pipeline_name, model_name, created_timestamp) VALUES (:pipeline_name, :model_name, :created_timestamp)")

        with engine.connect() as conn:
            result_pipeline = pd.read_sql_query(select_pipeline_query, conn, params={"pipeline_name": pipeline_name})
            if result_pipeline.empty:
                return {"error": "Pipeline not registered"}, 400
            else:
                result_model = pd.read_sql_query(select_model_query, conn, params={"model_name": models})
                if result_model.empty:
                    return {"error": "Model not registered"}, 400
                result_pipeline_model = pd.read_sql_query(select_pipeline_model_query, conn, params={"pipeline_name": pipeline_name, "model_name": models})
                if not result_pipeline_model.empty:
                    return {"error": "Pipeline and model already registered"}, 400
                
                for model in models:
                    conn.execute(insert_query, {"pipeline_name": pipeline_name, "model_name": model, "created_timestamp": created_timestamp})
                    #conn.commit()
                return {'message': 'Model added successfully'}, 201

    def get(self):
        select_query = "SELECT * FROM pipeline_model"

        with engine.connect() as conn:
            result = pd.read_sql_query(select_query, conn)
            if result.empty:
                return {"error": "No pipeline model association found"}, 400
            result['created_timestamp'] = result['created_timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            pipeline_list = result.to_dict(orient='records')
            return {'message': 'Listed all pipelines', 'pipeline_list': pipeline_list}, 200
        


@anomaly_namespace.route('')
class Anomalylog(Resource):
    @anomaly_namespace.expect(anomaly_model_field)
    def post(self):
        data = request.get_json()
        dataset = data.get('dataset')
        pipeline_name = data.get('pipeline')
        email = data.get('email')
        # timestamp = data['timestamp'] 
        timestamp = datetime.utcnow()
        anomalies = data.get('anomaly')

        insert_query = text("""
            INSERT INTO anomaly_log (
                dataset, pipeline_name, model_name, email, timestamp, 
                anomaly_type, number_of_instances, user_action
            ) 
            VALUES (
                :dataset, :pipeline_name, :model_name, :email, :timestamp, 
                :anomaly_type, :number_of_instances, :user_action
            )
        """)

        with engine.connect() as conn:
            for anomaly in anomalies:
                # Correct usage of anomaly item
                model_name = anomaly["model_name"]
                anomaly_type = anomaly["anomaly_type"]  # Correct key based on anomaly_detail model
                number_of_instances = anomaly["number_of_instances"]
                user_action = anomaly["user_action"]
                
                conn.execute(insert_query, {
                    "dataset": dataset, "pipeline_name": pipeline_name, "model_name": model_name,
                    "email": email, "timestamp": timestamp, "anomaly_type": anomaly_type,
                    "number_of_instances": number_of_instances, "user_action": user_action
                })
                #conn.commit()

        return {'message': 'Anomaly data submitted successfully'}, 201

    # def get(self):
    #     select_query = "SELECT * FROM pipeline_model"

    #     with engine.connect() as conn:
    #         result = pd.read_sql_query(select_query, conn)
    #         if result.empty:
    #             return {"error": "No pipeline model association found"}, 400
    #         result['created_timestamp'] = result['created_timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    #         pipeline_list = result.to_dict(orient='records')
    #         return {'message': 'Listed all pipelines', 'pipeline_list': pipeline_list}, 200
        


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000, debug=True)