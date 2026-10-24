from django.test import TestCase


class BrandingTests(TestCase):
    def test_login_page_uses_shared_brand_assets(self):
        response = self.client.get("/accounts/login/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "/static/accounts/images/studymate-mark.png",
        )
        self.assertContains(
            response,
            "/static/accounts/images/studymate-logo.png",
        )
        self.assertContains(response, 'class="site-footer"')
        self.assertContains(response, "Contact us")
        self.assertContains(
            response,
            "mailto:vishwavengadeshd@gmail.com",
        )
