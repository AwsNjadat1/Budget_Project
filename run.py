from budget_app import create_app

# Create the application instance using the factory function
app = create_app()

if __name__ == "__main__":
    print("🚀 Starting Budget Manager...")
    print("📊 Features: Enhanced UI/UX, Real-time calculations, Advanced filtering")
    print("🔗 Access the application at: http://localhost:5000")
    print("📁 Professional multi-file architecture is active!")
    
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=True
    )