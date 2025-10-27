from django import forms
from .models import Event
from datetime import datetime, time

class EventForm(forms.ModelForm):
    # separate date and time inputs, plus a single-day checkbox
    start_date = forms.DateField(required=True, widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}))
    start_time_only = forms.TimeField(required=True, widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"}))
    end_date = forms.DateField(required=True, widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}))
    end_time_only = forms.TimeField(required=True, widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"}))
    single_day = forms.BooleanField(required=False, initial=True, widget=forms.CheckboxInput())

    class Meta:
        model = Event
        fields = ["title", "description", "location"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "location": forms.TextInput(attrs={"class": "form-control"}),
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
