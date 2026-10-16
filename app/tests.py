from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from .models import SiteSetting


class SignupFlowTests(TestCase):
	def signup_data(self, **overrides):
		data = {
			'username': 'new-user',
			'email': 'new@example.com',
			'password1': 'StrongPassword123!',
			'password2': 'StrongPassword123!',
		}
		data.update(overrides)
		return data

	def test_signup_displays_policies_and_agreement_checkbox(self):
		response = self.client.get(reverse('signup'))

		self.assertContains(response, '利用規約')
		self.assertContains(response, 'プライバシーポリシー')
		self.assertContains(response, 'name="agreement"')

	def test_signup_requires_policy_agreement(self):
		response = self.client.post(reverse('signup'), self.signup_data())

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, '利用規約とプライバシーポリシーへの同意が必要です。')
		self.assertFalse(User.objects.filter(username='new-user').exists())

	def test_signup_with_agreement_redirects_to_completion(self):
		response = self.client.post(
			reverse('signup'),
			self.signup_data(agreement='on'),
		)

		self.assertRedirects(response, reverse('signup_done'))
		self.assertTrue(User.objects.filter(username='new-user').exists())
		self.assertContains(
			self.client.get(reverse('signup_done')),
			reverse('login'),
		)


class ContactFlowTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(
			username='contact-user',
			email='contact@example.com',
			password='StrongPassword123!',
		)

	def test_contact_requires_login(self):
		response = self.client.get(reverse('contact'))

		self.assertRedirects(response, f"{reverse('login')}?next={reverse('contact')}")

	def test_logged_in_user_can_send_contact(self):
		self.client.force_login(self.user)
		response = self.client.post(
			reverse('contact'),
			{'subject': '質問', 'message': 'お問い合わせ本文です。'},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'お問い合わせを受け付けました。')


class MaintenanceFlowTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(
			username='regular-user',
			password='StrongPassword123!',
		)
		self.admin = User.objects.create_user(
			username='site-admin',
			password='StrongPassword123!',
			is_staff=True,
		)

	def test_only_admin_can_change_maintenance_setting(self):
		self.client.force_login(self.user)
		response = self.client.get(reverse('maintenance_settings'))
		self.assertEqual(response.status_code, 302)

		self.client.force_login(self.admin)
		response = self.client.post(reverse('maintenance_settings'), {'maintenance_mode': 'on'})
		self.assertEqual(response.status_code, 200)
		self.assertTrue(SiteSetting.objects.get(pk=1).maintenance_mode)

	def test_regular_user_is_redirected_to_maintenance_after_login(self):
		SiteSetting.objects.create(pk=1, maintenance_mode=True)

		response = self.client.post(reverse('login'), {
			'username': 'regular-user',
			'password': 'StrongPassword123!',
		})

		self.assertRedirects(response, reverse('maintenance'))

	def test_admin_can_log_in_during_maintenance(self):
		SiteSetting.objects.create(pk=1, maintenance_mode=True)

		response = self.client.post(reverse('login'), {
			'username': 'site-admin',
			'password': 'StrongPassword123!',
		})

		self.assertRedirects(response, reverse('timeline'))
