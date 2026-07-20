FROM postgres:16-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip \
    && pip3 install --break-system-packages --no-cache-dir Faker==37.4.0 "psycopg[binary]>=3.2,<4" \
    && rm -rf /var/lib/apt/lists/*

COPY schema.sql /docker-entrypoint-initdb.d/01-schema.sql
COPY init_seed.sh /docker-entrypoint-initdb.d/02-seed.sh
COPY seed_data.py /opt/harness/seed_data.py
RUN chmod +x /docker-entrypoint-initdb.d/02-seed.sh /opt/harness/seed_data.py

