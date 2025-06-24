from app import create_app
import os


application = create_app()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    application.run(debug=True, port=port, host='0.0.0.0')
    
