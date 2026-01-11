from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("base", "0009_delete_spamfilter"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "CREATE TABLE IF NOT EXISTS ratelimit_cache ("
                "cache_key varchar(255) NOT NULL PRIMARY KEY, "
                "value text NOT NULL, "
                "expires timestamp with time zone NOT NULL"
                ");"
            ),
            reverse_sql="DROP TABLE IF EXISTS ratelimit_cache;",
        ),
    ]