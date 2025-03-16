from flask import Flask
from routes import main_routes
from config import config

app = Flask(__name__)

app.config.from_object(config)

app.register_blueprint(main_routes)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.PORT_START_SERVIS, debug=True)
