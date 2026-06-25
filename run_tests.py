import sys
import traceback

print("Testing Application Initialization...")
try:
    from app import app, db, User
    with app.app_context():
        # Setup test client
        client = app.test_client()
        
        print("Testing Home/Login page...")
        res = client.get('/')
        assert res.status_code == 200, f"Failed to load home page: {res.status_code}"
        print("Home page loaded successfully.")

        print("\nAll basic load tests passed successfully!")
except Exception as e:
    print("Error during test:")
    traceback.print_exc()
    sys.exit(1)
