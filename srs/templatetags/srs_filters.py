from django import template
import math

register = template.Library()

@register.filter(name='multiply')
def multiply(value, arg):
    """Multiply the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter(name='sm2_interval')
def sm2_interval(card, quality):
    """Calculate the SM-2 interval for a given quality rating"""
    from ..algorithms import sm2_update, SM2State
    
    try:
        quality = int(quality)
        if quality not in [1, 3, 4, 5]:  # Again, Hard, Good, Easy
            return "1d"
        
        # Create current SM-2 state from card
        current_state = SM2State(
            ease_factor=card.ease_factor,
            interval=card.interval,
            repetitions=card.repetitions,
            due=card.due
        )
        
        # Calculate what the interval would be for this quality
        result = sm2_update(current_state, quality)
        interval = result.new_state.interval
        
        # Return formatted interval
        if interval == 1:
            return "1d"
        elif interval < 7:
            return f"{interval}d"
        elif interval < 30:
            weeks = interval // 7
            remaining_days = interval % 7
            if weeks == 1:
                if remaining_days == 0:
                    return "1w"
                else:
                    return f"1w{remaining_days}d"
            else:
                if remaining_days == 0:
                    return f"{weeks}w"
                else:
                    return f"{weeks}w{remaining_days}d"
        elif interval < 365:
            months = interval // 30
            remaining_days = interval % 30
            if months == 1:
                if remaining_days == 0:
                    return "1m"
                else:
                    return f"1m{remaining_days}d"
            else:
                if remaining_days == 0:
                    return f"{months}m"
                else:
                    return f"{months}m{remaining_days}d"
        else:
            years = interval // 365
            remaining_days = interval % 365
            if years == 1:
                if remaining_days == 0:
                    return "1y"
                else:
                    return f"1y{remaining_days}d"
            else:
                if remaining_days == 0:
                    return f"{years}y"
                else:
                    return f"{years}y{remaining_days}d"
                    
    except (ValueError, TypeError, AttributeError):
        return "1d"