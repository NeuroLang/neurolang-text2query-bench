# Export the API keys of ~/.zshrc for non-interactive shells, without
# printing them:  source scripts/env.sh
export ALBERT_API_KEY=$(zsh -ic 'print -r -- $ALBERT_KEY' 2>/dev/null | tail -1)
export OPENROUTER_API_KEY=$(zsh -ic 'print -r -- $OPENROUTER_API_KEY' 2>/dev/null | tail -1)
export SSL_CERT_FILE=/etc/ssl/cert.pem
