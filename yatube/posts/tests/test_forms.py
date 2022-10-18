import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Group, Post, User, Comment

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создаем запись в базе данных для
        # проверки сушествующего slug
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug1',
            description='test-slug2',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.post.author,
            text='Текст тестового комментария'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # Создаем клиент
        self.author_client = Client()
        self.author_client.force_login(self.post.author)

    def test_create_post(self):
        """Валидная форма создает запись в Пост."""
        posts_count = Post.objects.all().count()

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )

        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

        form_data = {
            'group': self.group.id,
            'author': self.user.id,
            'text': 'Тест текст',
            'image': uploaded,
        }

        response = self.author_client.post(
            reverse('posts:post_create'),
            data=form_data,
        )
        self.assertRedirects(
            response, reverse(
                'posts:profile', kwargs={'username': self.post.author}
            )
        )

        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text='Тест текст',
                author=self.user.id,
                group=self.group.id,
            ).exists()
        )
        post = Post.objects.filter(
            text='Тест текст',
            author=self.user.id,
            group=self.group.id,
        ).last()

        self.assertEqual(str(post.image), 'posts/small.gif')
        self.assertEqual(response.status_code, 302)

    def test_edit_post(self):
        """Валидная форма редактирует запись в Пост."""
        posts_count = Post.objects.count()
        self.post = PostFormTests.post
        form_data = {
            'group': self.group.id,
            'author': self.user.id,
            'text': 'Тест текс1т',
        }

        response = self.author_client.post(
            reverse('posts:post_edit', args=(f'{self.post.pk}',)),
            data=form_data,
            follow=True
        )
        post2 = Post.objects.get(id=self.post.pk)
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertEqual(post2.author, self.post.author)
        self.assertEqual(post2.group.pk, self.group.pk)
        self.assertEqual(post2.text, 'Тест текс1т')
        self.assertEqual(response.status_code, 200)

    def test_comment_form(self):
        """Валидная форма КОММЕНТОВ."""
        self.comment = PostFormTests.comment
        form_data = {
            'post': PostFormTests.post,
            'author': PostFormTests.post.author,
            'text': 'Текст тестового комментария'
        }

        response = self.author_client.post(
            reverse('posts:post_detail', args=(f'{self.post.pk}',)),
            data=form_data,
        )
        self.assertTrue(
            Comment.objects.filter(
                text='Текст тестового комментария',
                author=self.post.author.id,
                post=self.post.id
            ).exists()
        )
        self.assertEqual(response.status_code, 200)

    def test_imageform_no_image(self):
        """в поле фото не то вставляется."""

        small_aac = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )

        uploaded = SimpleUploadedFile(
            name='small.aac',
            content=small_aac,
            content_type='image/aac'
        )

        form_data = {
            'group': self.group.id,
            'author': self.user.id,
            'text': 'Тест текст',
            'image': uploaded,
        }

        response = self.author_client.post(
            reverse('posts:post_create'),
            data=form_data,
        )
        self.assertFormError(
            response,
            'form',
            'image',
            "Формат файлов 'aac' не поддерживается. Поддерживаемые форматы"
            + " файлов: 'bmp, dib, gif, tif, tiff, jfif, jpe, jpg, jpeg,"
            + " pbm, pgm, ppm, pnm, png, apng, blp, bufr, cur, pcx, dcx,"
            + " dds, ps, eps, fit, fits, fli, flc, ftc, ftu, gbr, grib,"
            + " h5, hdf, jp2, j2k, jpc, jpf, jpx, j2c, icns, ico, im, iim,"
            + " mpg, mpeg, mpo, msp, palm, pcd, pdf, pxr, psd, bw, rgb,"
            + " rgba, sgi, ras, tga, icb, vda, vst, webp, wmf, emf, xbm, xpm'."
        )
