from django import forms
from .models import Event

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["title", "description", "location", "start_time", "end_time"]
        widgets = {
            "start_time": forms.DateTimeInput(attrs={"type":"datetime-local", "class":"form-control"}),
            "end_time": forms.DateTimeInput(attrs={"type":"datetime-local", "class":"form-control"}),
            "title": forms.TextInput(attrs={"class":"form-control"}),
            "description": forms.Textarea(attrs={"class":"form-control", "rows":3}),
            "location": forms.TextInput(attrs={"class":"form-control"}),
        }
