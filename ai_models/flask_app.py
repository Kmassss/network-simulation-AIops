from flask import Flask


def create_app():
    app = Flask(__name__)

    # app.config.from_object()

    from  ai_models.route.inference_bp import inference_bp


    app.register_blueprint(inference_bp,url_prefix = '/inference')

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )

