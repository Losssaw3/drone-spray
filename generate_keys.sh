#!/bin/bash

# Скрипт: generate_keys.sh
# Назначение: Генерация RSA ключей для ЭЦП в PEM-формате
# Требует: OpenSSL

# Параметры
KEY_SIZE=2048           # Размер ключа (2048/3072/4096)
PRIVATE_KEY="private_key.pem"  # Файл приватного ключа
PUBLIC_KEY="public_key.pem"    # Файл публичного ключа

# Генерация приватного ключа
echo "🔐 Генерация приватного ключа RSA-$KEY_SIZE..."
openssl genpkey \
    -algorithm RSA \
    -pkeyopt rsa_keygen_bits:$KEY_SIZE \
    -out $PRIVATE_KEY

if [ $? -ne 0 ]; then
    echo "❌ Ошибка генерации приватного ключа!"
    exit 1
fi

# Извлечение публичного ключа
echo "🔑 Извлечение публичного ключа..."
openssl rsa \
    -in $PRIVATE_KEY \
    -pubout \
    -out $PUBLIC_KEY

if [ $? -ne 0 ]; then
    echo "❌ Ошибка извлечения публичного ключа!"
    exit 1
fi

# Установка прав доступа
chmod 600 $PRIVATE_KEY
chmod 644 $PUBLIC_KEY
echo "✅ Успешно сгенерированы:"
echo "   • Приватный ключ: $PRIVATE_KEY"
echo "   • Публичный ключ: $PUBLIC_KEY"