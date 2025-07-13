import os
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
from datetime import datetime

# Use a proxy for the database so we can initialize it later.
db_proxy = Proxy()

class BaseModel(Model):
    class Meta:
        database = db_proxy

class User(BaseModel):
    id = IntegerField(primary_key=True)
    name = CharField(unique=True)

class File(BaseModel):
    id = IntegerField(primary_key=True)
    path = TextField()
    version = IntegerField()
    content = TextField()
    timestamp = DateTimeField(default=datetime.now)

    class Meta:
        indexes = (
            # Create a unique index on path and version
            (('path', 'version'), True),
        )

class Chat(BaseModel):
    id = IntegerField(primary_key=True)
    user = ForeignKeyField(User, backref='chats')
    message = TextField()
    timestamp = DateTimeField(default=datetime.now)

def initialize_database(directory):
    """Initializes the database connection and creates tables."""
    db_path = os.path.join(directory, '.lin.db')
    database = SqliteDatabase(db_path)
    db_proxy.initialize(database)

    with db_proxy:
        db_proxy.create_tables([User, File, Chat], safe=True)

        # Pre-populate users if they don't exist
        User.get_or_create(name='brent')
        User.get_or_create(name='linus')

    return database
