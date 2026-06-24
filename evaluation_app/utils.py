from rest_framework import serializers

class LabelChoiceField(serializers.ChoiceField):
    def to_internal_value(self, data):
        data_str = str(data)
        if data_str in self.choices:
            return data_str
        for key, label in self.choices.items():
            if label == data:
                return key

        for key, label in self.choices.items():
            if label.lower() == data_str.lower():
                return key      
        self.fail('invalid_choice', input=data)
    def to_representation(self, value):
        return self.choices.get(value, super().to_representation(value))
