import sqlalchemy
from google.cloud.sql.connector import Connector
import os

INSTANCE_CONNECTION_NAME = "terraform-482817:us-central1:db-instance"
DB_NAME = "appdb"
DB_USER = "appuser"

connector = Connector()

def getconn():
    conn = connector.connect(
        INSTANCE_CONNECTION_NAME,
        "pg8000",
        user=DB_USER,
        password=os.environ["DB_PASSWORD"],
        db=DB_NAME,
    )
    return conn

engine = sqlalchemy.create_engine(
    "postgresql+pg8000://",
    creator=getconn,
    pool_size=5,
    max_overflow=2,
    pool_timeout=30,
    pool_recycle=1800,
)
