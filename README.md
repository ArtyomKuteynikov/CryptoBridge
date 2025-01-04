# CryptoBridge

https://cryptobridge.space/

CryptoBridge is a cryptocurrency designed to provide maximum ease of connection to cryptocurrency exchanges and platforms. We understand how critical blockchain integration is with existing infrastructures, and we’re building a solution focused on simplicity, scalability, and compatibility with all exchanges.

<hr>

# DataBase

CryptoBridge uses MongoDB for fast operations and easy integration with an API

### Install MongoDB on Ubuntu
https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-ubuntu/

<hr>

# Options

CryptoBridge is decentralised blockchain, so you can run node on your own server. Our node includes an API, so you can easily integrate it with your project (e.g. exchanges, payment systems, etc.). 

As an option you can turn API or Mining off to save server resources if you want just information node or just mining

<hr>

# Create release

If you made significant changes in blockchain that improves functionality, stability or efficiency you can build your own release

## On windows:

```
pyinstaller --onefile --add-data "config.ini:." run.py --name cryptobridge-windows
```

## On linux:

```
pyinstaller --onefile --add-data "config.ini:." run.py --name cryptobridge-linux
```

<hr>

# Requirements:

1. Python 3.9+ 
2. FastAPI package to run api
3. Uvcorn package to run api
4. Pydantic package to describe API schemas
5. PyMongo package to interact with MongoDB
6. PyCryptoDome package to use RIPEMD160 cause OpenSSL removed this algorithm for furthest versions

<hr>

# Roadmap:

- [x] Open dev access to blockchain
- [ ] Add ability to run self-hosted nodes
- [ ] Deploy python client to PyPi 
- [ ] Add Shield wallets
- [ ] Add Escrow transactions
- [ ] Add support for deploying new tokens on-chain
