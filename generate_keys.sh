#!/bin/bash

# Скрипт: generate_keys.sh

KEY_SIZE=2048
PRIVATE_KEY="shared/private_key.pem"
PUBLIC_KEY="shared/public_key.pem"

# Генерация приватного ключа
openssl genpkey \
    -algorithm RSA \
    -pkeyopt rsa_keygen_bits:$KEY_SIZE \
    -out $PRIVATE_KEY

if [ $? -ne 0 ]; then
    exit 1
fi

# Извлечение публичного ключа
openssl rsa \
    -in $PRIVATE_KEY \
    -pubout \
    -out $PUBLIC_KEY

if [ $? -ne 0 ]; then
    exit 1
fi

# Установка прав доступа
chmod 644 $PRIVATE_KEY
chmod 644 $PUBLIC_KEY
echo "   • Приватный ключ: $PRIVATE_KEY"
echo "   • Публичный ключ: $PUBLIC_KEY"