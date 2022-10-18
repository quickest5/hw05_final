from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from ..models import Group, Post

User = get_user_model()


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug1',
            description='test-slug2',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='HasNoName')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.author_client = Client()
        self.author_client.force_login(self.post.author)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        # Шаблоны по адресам
        templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{StaticURLTests.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.user}/': 'posts/profile.html',
            f'/posts/{self.post.pk}/': 'posts/post_detail.html',
            '/about/author/': 'about/author.html',
            '/about/tech/': 'about/tech.html',

        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_wrong_uri_returns_404(self):
        """проверка на использование кастомной страницы ошибки"""
        response = self.client.get('something/really/weird/')
        template = 'core/404.html'
        self.assertTemplateUsed(response, template)

    def test_post_list_url_exists_at_desired_location(self):
        """Страница /create/ доступна авторизованному пользователю."""
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.status_code, 200)

    def test_post_detail_url_redirect_authorized_not_author(self):
        """Страница по адресу /post/self.post.pk/edit
        перенаправит пользователя не автора
        """
        response = self.authorized_client.get(
            f'/posts/{self.post.pk}/edit/',
            follow=True
        )
        self.assertRedirects(
            response, f'/posts/{self.post.pk}/'
        )

    def test_post_detail_get_author_200(self):
        """Страница изменения доступа автору
        /post/self.post.pk/edit даст зайти автору
        """
        response = self.author_client.get(
            f'/posts/{self.post.pk}/edit/',
        )
        self.assertEqual(
            response.status_code, 200
        )

    def test_create_method_get_post(self):
        """переадресация гостя к /create/ через GET/POST"""
        responses_302 = (
            '/create/',
        )
        for value in responses_302:
            with self.subTest(value):
                self.assertEqual(
                    self.guest_client.get(value).status_code,
                    HTTPStatus.FOUND,
                    ('гость по ссылке /create/ метод GET '
                     'не смог перейтиб должна быть переадресация')
                )
            with self.subTest(value):
                self.assertEqual(
                    self.guest_client.post(value).status_code,
                    HTTPStatus.FOUND,
                    ('гость по ссылке /create/ метод POST'
                     ' не смог перейти, должна быть переадресация')
                )

    def test_pos_method_post(self):
        """"""
        responses_302 = (
            f'/posts/{self.post.pk}/edit/',
        )
        for value in responses_302:
            with self.subTest(value):
                self.assertEqual(
                    self.authorized_client.post(value).status_code,
                    HTTPStatus.FOUND,
                    ('не автора по ссылке не редиректнуло')
                )

    def test_follow_index(self):
        """Страница /follow_index/ не доступна ноунейму."""
        response = self.guest_client.get('/follow/')
        self.assertEqual(response.status_code, 302)

    def test_comments_guest_user(self):
        response = self.guest_client.get(f'/posts/{self.post.pk}/comment/')
        self.assertEqual(response.status_code, 302)
