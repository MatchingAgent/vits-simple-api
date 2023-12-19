import uvicorn
from fastapi import FastAPI

from tts_app_fastapi.routes.healthcheck import router as healthcheckRouter
from tts_app_fastapi.routes.voice import router as voiceRouter
from utils.config_manager import global_config



app = FastAPI()


class VitsSimpleApi:
    def __init__(self):
        self.__app = FastAPI()

    def setup(self):
        self.__app.include_router(healthcheckRouter)
        self.__app.include_router(voiceRouter)
        

    def run(self):
        config = uvicorn.Config(
            self.__app,
            host="0.0.0.0",
            port=23456,
            log_config=None,
            access_log=False,
            timeout_keep_alive=65,
        )
        server = uvicorn.Server(config)
        server.run()


if __name__ == "__main__":
    app = VitsSimpleApi()
    app.setup()
    app.run()
