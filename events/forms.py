from django import forms
from .models import Event
from datetime import datetime, time
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import Country, Community, Profile, EventImage

class EventForm(forms.ModelForm):
    # separate date and time inputs, plus a single-day checkbox
    start_date = forms.DateField(required=True, widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}))
    start_time_only = forms.TimeField(required=True, widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"}))
    end_date = forms.DateField(required=True, widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}))
    end_time_only = forms.TimeField(required=True, widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"}))
    single_day = forms.BooleanField(required=False, initial=True, widget=forms.CheckboxInput())
    # allow selecting additional organizers (owner remains primary)
    organizers = forms.ModelMultipleChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-control select2"})
    )

    class Meta:
        model = Event
        fields = ["title", "description", "location", "event_type", "country", "targeted_communities", "organizers"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "location": forms.TextInput(attrs={"class": "form-control"}),
            "event_type": forms.Select(attrs={"class": "form-control"}),
            "country": forms.Select(attrs={"class": "form-control"}),
            # use a multi-select <select> which will be enhanced by Select2 to show tokenized selections
            "targeted_communities": forms.SelectMultiple(attrs={"class": "form-control select2"}),
        }

    def __init__(self, *args, **kwargs):
        # accept instance to initialize date/time fields
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            st = self.instance.start_time
            en = self.instance.end_time
            if st:
                self.fields['start_date'].initial = st.date()
                self.fields['start_time_only'].initial = st.time().replace(microsecond=0)
            if en:
                self.fields['end_date'].initial = en.date()
                self.fields['end_time_only'].initial = en.time().replace(microsecond=0)
            # default single_day when dates equal
            if st and en and st.date() == en.date():
                self.fields['single_day'].initial = True
            else:
                self.fields['single_day'].initial = False
        else:
            # sensible defaults
            today = datetime.now().date()
            self.fields['start_date'].initial = today
            self.fields['end_date'].initial = today
            self.fields['start_time_only'].initial = time(hour=9, minute=0)
            self.fields['end_time_only'].initial = time(hour=10, minute=0)
            self.fields['single_day'].initial = True

    def clean(self):
        cleaned = super().clean()
        sd = cleaned.get('start_date')
        st = cleaned.get('start_time_only')
        ed = cleaned.get('end_date')
        et = cleaned.get('end_time_only')
        single = cleaned.get('single_day')

        if sd is None or st is None:
            raise forms.ValidationError('Start date and time are required')

        if single:
            # force end date to be same as start
            ed = sd
            cleaned['end_date'] = ed

        if ed is None or et is None:
            raise forms.ValidationError('End date and time are required')

        # combine into datetimes
        start_dt = datetime.combine(sd, st)
        end_dt = datetime.combine(ed, et)

        if end_dt < start_dt:
            raise forms.ValidationError('End must be after start')

        cleaned['start_time'] = start_dt
        cleaned['end_time'] = end_dt
        return cleaned

    def save(self, commit=True):
        # set model's DateTimeFields from combined fields
        self.instance.start_time = self.cleaned_data['start_time']
        self.instance.end_time = self.cleaned_data['end_time']
        return super().save(commit=commit)


class RegistrationForm(UserCreationForm):
    # Ask for first and last name instead of username; username will be auto-generated
    first_name = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={"class": "form-control"}))
    last_name = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={"class": "form-control"}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={"class": "form-control"}))
    country = forms.ModelChoiceField(queryset=Country.objects.all(), required=True, widget=forms.Select(attrs={"class": "form-control"}))
    community = forms.ModelChoiceField(queryset=Community.objects.all(), required=True, widget=forms.Select(attrs={"class": "form-control"}))

    class Meta:
        model = get_user_model()
        fields = ("first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # remove the username field from the form so the user isn't asked for it
        if 'username' in self.fields:
            self.fields.pop('username')
        # ensure password fields have bootstrap classes
        for name in ('password1', 'password2'):
            if name in self.fields:
                self.fields[name].widget.attrs.update({"class": "form-control"})

    def _slugify_name(self, first, last):
        # create a basic ascii-lowercase username from first and last name
        import re
        base = f"{first}_{last}".strip()
        # replace non-alphanumeric characters with underscore
        base = re.sub(r'[^0-9a-zA-Z_]+', '_', base)
        base = base.lower()
        # trim to Django username max length (150)
        return base[:150]

    def _generate_unique_username(self, first, last):
        User = get_user_model()
        base = self._slugify_name(first, last)
        username = base
        # if username exists, append numeric suffixes until unique
        counter = 1
        while User.objects.filter(username=username).exists():
            suffix = f"_{counter}"
            # ensure we don't exceed 150 chars
            allowed = 150 - len(suffix)
            username = (base[:allowed]) + suffix
            counter += 1
        return username

    def clean_email(self):
        """Ensure the email address is unique (case-insensitive)."""
        email = self.cleaned_data.get('email', '').strip()
        User = get_user_model()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('A user with that email already exists.')
        return email

    def save(self, commit=True):
        User = get_user_model()
        first = self.cleaned_data.get('first_name', '')
        last = self.cleaned_data.get('last_name', '')
        email = self.cleaned_data.get('email', '').strip()
        username = self._generate_unique_username(first, last)

        # create the user using the provided password
        password = self.cleaned_data.get('password1')
        user = User.objects.create_user(username=username, password=password, email=email)
        user.first_name = first
        user.last_name = last
        if commit:
            user.save()

        # create Profile
        country = self.cleaned_data.get('country')
        community = self.cleaned_data.get('community')
        Profile.objects.create(user=user, country=country, community=community)
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("country", "community")
        widgets = {
            'country': forms.Select(attrs={"class": "form-control"}),
            'community': forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # allow empty selection (Profile.country/community are nullable)
        self.fields['country'].required = False
        self.fields['community'].required = False


class EventImageForm(forms.ModelForm):
    class Meta:
        model = EventImage
        fields = ('image',)
        widgets = {
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'})
        }


class NameLoginForm(forms.Form):
    """Login form that asks for email + password instead of name/family name.

    We keep the old name `NameLoginForm` as an alias for compatibility with
    existing imports, but the form now accepts `email` and `password`.
    """
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={"class": "form-control"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get('email', '').strip()
        if not email:
            raise forms.ValidationError('Email is required.')
        return cleaned

# maintain backward-compatible name
EmailLoginForm = NameLoginForm
