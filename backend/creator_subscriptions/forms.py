from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model


User = get_user_model()


class EmailRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email


class MockXConnectForm(forms.Form):
    x_user_id = forms.CharField(
        label='X user ID',
        max_length=64,
        help_text='Try mock-premium, mock-basic, mock-plus, or mock-unsubscribed.',
    )


class MockXSignInForm(MockXConnectForm):
    confirmed_email = forms.EmailField(
        required=False,
        help_text='Optional. If it matches an existing email user, that account is linked.',
    )
