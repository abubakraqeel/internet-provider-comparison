from app import create_app
from dotenv import load_dotenv


app = create_app()

if __name__ == '__main__':
    # load_dotenv("/Users/abubakraqeel/dev/check24/.env")
    app.run(debug=True)
    
