import os
from datetime import datetime
from peewee import (
    Model,
    SqliteDatabase,
    CharField,
    TextField,
    DateTimeField,
    IntegerField,
    ForeignKeyField,
    Proxy
)
from .config import USER_NAME, PARTNER_NAME
from .logger import debug

# Use a proxy for the database so we can initialize it later.
db_proxy = Proxy()

class BaseModel(Model):
    class Meta:
        database = db_proxy

class User(BaseModel):
    id = IntegerField(primary_key=True)
    name = CharField(unique=True)

class Chat(BaseModel):
    id = IntegerField(primary_key=True)
    user = ForeignKeyField(User, backref='chats')
    message = TextField()
    timestamp = DateTimeField(default=datetime.now)

def initialize_database(cwd):
    """Initializes the database connection and creates tables."""
    db_path = os.path.join(cwd, '.lin.db')
    database = SqliteDatabase(db_path)
    db_proxy.initialize(database)

    with db_proxy:
        db_proxy.create_tables([User, Chat], safe=True)

        # Pre-populate users if they don't exist
        User.get_or_create(name=USER_NAME.lower())
        User.get_or_create(name=PARTNER_NAME.lower())

    debug(f"Using sqlite database: {database.database}")

    return database
