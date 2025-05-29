# Tenant First Aid

A chatbot that provides legal advice related to housing and eviction

Live at https://tenantfirstaid.com/

## Local Development

### Prerequisites
 - [uv](https://docs.astral.sh/uv/getting-started/installation/)
 - [docker](https://www.docker.com/)

1. copy `backend/.env.example` to a new file named `.env` in the same directory and populate it with your `OPENAI_API_KEY`. You can set an invalid key, in which case the bot will return error messages. This may still be useful for developing other features.
1. `cd backend`
1. `docker-compose up` (use `-d` if you want to run this in the background, otherwise open a new terminal)
1. `uv sync`
1. If you have not uploaded the Oregon Housing Law documents to a vector store in OpenAI, run `uv run scripts/create_vector_store.py` and follow the instructions to add the vector store ID to your `.env`.
1. `uv run python -m tenantfirstaid.app`
1. Open a new terminal / tab
1. `cd ../frontend`
1. `npm install`
1. `npm run dev`
1. Go to http://localhost:5173
1. Start chatting

### Run backend tests

In the `backend/` directory, run `uv run pytest`

## Contributing

We currently have regular project meetups: https://www.meetup.com/codepdx/ . Also check out https://www.codepdx.org/ to find our Discord server.

## Remote server setup
On DO, we:
1. added our ssh public keys
2. install nginx
3. Kent got the tls cert (just ask chatgpt?)

## Additional features

go to the route `/feedback` for extra features. You will need to provide the password defined in your `.env` file.
