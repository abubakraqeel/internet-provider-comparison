from app import create_app



app = create_app()

if __name__ == '__main__':
    # load_dotenv("/Users/abubakraqeel/dev/check24/.env")
    app.run(debug=True)
    
