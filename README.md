# Halu-Insure 🔥

A decentralized multi-agent AI verification system built using:

* FastAPI
* Groq LLM APIs
* Solidity Smart Contracts
* Ethereum Sepolia
* Web3.py
* React + Vite
* TailwindCSS

---

# 🚀 Project Overview

Halu-Insure is an experimental AI honesty verification system.

Flow:

```text
User Question
   ↓
Prover AI generates answer
   ↓
Confidence score generated
   ↓
Auditor AI checks honesty
   ↓
Blockchain stake transaction executed
   ↓
Hallucination decision made
   ↓
Frontend displays result
```

The goal is to create financially accountable AI systems using blockchain.

---

# 🧠 Features

## AI System

* Prover AI generates answers
* Confidence scoring
* Auditor AI verifies honesty
* Hallucination detection
* Structured JSON validation

## Blockchain

* Solidity smart contract
* ETH staking system
* Trust score tracking
* Slash/release logic
* Sepolia deployment

## Backend

* FastAPI
* Swagger docs
* Web3.py integration
* Real Sepolia transactions

## Frontend

* React + Vite
* TailwindCSS
* Dark modern UI
* Live AI responses
* Blockchain tx hashes

---

# 📁 Project Structure

```text
halu-insure/
│
├── backend/
│   ├── main.py
│   ├── prover.py
│   ├── auditor.py
│   ├── blockchain.py
│   ├── models.py
│   ├── requirements.txt
│   └── .env
│
├── contracts/
│   └── HaluInsure.sol
│
├── scripts/
│   └── deploy.js
│
├── frontend/
│   ├── src/
│   └── package.json
│
├── hardhat.config.js
├── package.json
└── .env
```

---

# ⚙️ Requirements

Install:

* Node.js (18+ recommended)
* Python 3.11+
* MetaMask
* Git

---

# 🔐 IMPORTANT

This repo DOES NOT include:

* root `.env`
* `backend/.env`

These contain private keys and API keys.

Every teammate must create them manually.

---

# 🛠️ ROOT `.env` SETUP

Create:

```text
halu-insure/.env
```

Add:

```env
SEPOLIA_RPC_URL=https://sepolia.infura.io/v3/YOUR_KEY
PRIVATE_KEY=YOUR_METAMASK_PRIVATE_KEY
```

Used by:

* Hardhat
* Smart contract deployment

---

# 🛠️ BACKEND `.env` SETUP

Create:

```text
halu-insure/backend/.env
```

Add:

```env
GROQ_API_KEY=YOUR_GROQ_API_KEY

SEPOLIA_RPC_URL=https://sepolia.infura.io/v3/YOUR_KEY

HALU_CONTRACT_ADDRESS=DEPLOYED_CONTRACT_ADDRESS

BACKEND_PRIVATE_KEY=YOUR_METAMASK_PRIVATE_KEY
```

---

# 🌐 Sepolia Setup

## 1. Install MetaMask

[https://metamask.io/](https://metamask.io/)

## 2. Switch to Sepolia

Enable:

* "Show test networks"

Then select:

* Ethereum Sepolia

## 3. Get Sepolia ETH

Use faucet:

[https://sepolia-faucet.pk910.de/](https://sepolia-faucet.pk910.de/)

or

[https://www.alchemy.com/faucets/ethereum-sepolia](https://www.alchemy.com/faucets/ethereum-sepolia)

---

# 📦 Install Dependencies

---

## Backend

Open terminal:

```bash
cd backend
```

Install:

```bash
pip install -r requirements.txt
pip install web3
```

---

## Frontend

Open terminal:

```bash
cd frontend
```

Install:

```bash
npm install
```

---

## Smart Contract / Hardhat

From project root:

```bash
npm install
```

---

# 🚀 Run Backend

From:

```bash
cd backend
```

Run:

```bash
uvicorn main:app --reload
```

Backend URL:

```text
http://127.0.0.1:8000
```

Swagger Docs:

```text
http://127.0.0.1:8000/docs
```

---

# 🚀 Run Frontend

From:

```bash
cd frontend
```

Run:

```bash
npm run dev
```

Frontend URL:

```text
http://localhost:5173
```

---

# ⛓️ Deploy Smart Contract

From project root:

Compile:

```bash
npm run compile
```

Deploy:

```bash
npm run deploy:sepolia
```

After deployment:

Copy contract address into:

```text
backend/.env
```

Example:

```env
HALU_CONTRACT_ADDRESS=0x123...
```

---

# 🧪 Test the Backend

Open:

```text
http://127.0.0.1:8000/docs
```

Use:

## POST `/query`

Example:

```json
{
  "question": "What is blockchain?"
}
```

Expected flow:

* AI generates answer
* Confidence score created
* Blockchain stake tx executes
* Auditor verifies response
* Final result returned

---

# 🔥 Current MVP Features

✅ AI prover

✅ AI auditor

✅ Confidence scoring

✅ Hallucination detection

✅ Solidity smart contract

✅ Sepolia deployment

✅ Real blockchain transactions

✅ FastAPI backend

✅ React frontend

✅ End-to-end integration

---

# 🧠 Future Improvements

* MetaMask wallet connect
* RAG-based auditor
* Dispute system
* Better UI animations
* Analytics dashboard
* Contract verification
* Live Etherscan links

---

# 👨‍💻 Team Notes

## Important Files

### Backend

* `main.py` → main API flow
* `prover.py` → AI answer generation
* `auditor.py` → AI verification
* `blockchain.py` → Web3 interactions

### Smart Contracts

* `contracts/HaluInsure.sol`

### Frontend

* React components inside `frontend/src`

---

# ⚠️ Security Notes

DO NOT:

* commit `.env`
* expose private keys
* use mainnet wallet private keys

Use only test wallets for Sepolia.

---

# 🏆 Built For

RV College of Engineering

Experiential Learning Phase 1

2025–26

---

# 🔥 Build Philosophy

```text
Build → Verify → Stake → Audit → Decide
```
