import click
import os
from peewee import *

def get_db_path():
    return os.environ.get('DATABASE','./db.sqlite') # recuperer le chemin de la base de donnee a partir d'une variable d'environnement sinon mette dans ./

class BaseModel(Model): #une classe de base pour tous les models de donnees de l'applicatopn
    class Meta: # fournit des metadonnes specifiques a la classe BaseModel
        database = SqliteDatabase(get_db_path())

class User(BaseModel):
    id = IntegerField(primary_key=True)
    email = CharField()
    password = CharField()

class conversation_history(BaseModel):
    id = IntegerField(primary_key=True)
    id_user = IntegerField()
    session_id = CharField()
    role = CharField()
    message = CharField(max_length=750)

class current_user(BaseModel):
    id = IntegerField(primary_key=True)
    user_id = IntegerField()



def init_db_command():
    mesModeles = [User,conversation_history,current_user]
    database = SqliteDatabase(get_db_path())
    try:
        database.create_tables(mesModeles)
        click.echo("Initialized the database. ")
    except:
        click.echo("Table already exist ...")

# Cette fonction permet de lancer les commandes
def cli():
    init_db_command()

