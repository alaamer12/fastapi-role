from fastapi import FastAPI
import fastapi_role
from fastapi_role import RBACService

print("Successfully imported fastapi_role version:", fastapi_role.__version__)
print("RBACService is available:", RBACService)

app = FastAPI()
