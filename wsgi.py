from app import create_app

# Cria a instância da aplicação - o scheduler é gerenciado internamente agora
app = create_app()

if __name__ == "__main__":
    app.run()
