from fastapi import FastAPI
from app.routes import user
from fastapi.staticfiles import StaticFiles

############ db
# fake_users_db = {
#     "johndoe": {
#         "username": "johndoe",
#         "full_name": "John Doe",
#         "email": "johndoe@example.com",
#         "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
#         "disabled": False,
#     }
# }
#
# print(fake_users_db)
# print(type(fake_users_db))
############

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(user.router)
