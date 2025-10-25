# Generated manually for adding user_book field to Order model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('books', '0009_book_image_features_userbook_image_features'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='user_book',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='books.userbook'),
        ),
        migrations.AlterField(
            model_name='order',
            name='book',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='books.book'),
        ),
    ]
