from app import create_app
from app.routes import trocr_route

app = create_app()
app.include_router(trocr_route.router)

if __name__ == '__main__':
    app.run(debug=True)
