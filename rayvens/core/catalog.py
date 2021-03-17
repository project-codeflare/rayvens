# construct a camel source specification from a rayvens source config
def construct_source(config, endpoint, inverted=False):
    if 'kind' not in config:
        raise TypeError('A Camel source needs a kind.')
    if config['kind'] not in ['http-source']:
        raise TypeError('Unsupported Camel source.')
    if 'url' not in config:
        raise TypeError('Kind http-source requires a url.')
    url = config['url']
    period = config.get('period', 1000)

    if inverted:
        return [{
            'from': {
                'uri': f'timer:tick?period={period}',
                'steps': [{
                    'to': url
                }, {
                    'bean': 'addToQueue'
                }]
            },
        }, {
            'from': {
                'uri': endpoint,
                'steps': [{
                    'bean': 'takeFromQueue'
                }]
            }
        }]
    else:
        return [{
            'from': {
                'uri': f'timer:tick?period={period}',
                'steps': [{
                    'to': url
                }, {
                    'to': endpoint
                }]
            }
        }]


# construct a camel sink specification from a rayvens sink config
def construct_sink(config, endpoint):
    if 'kind' not in config:
        raise TypeError('A Camel sink needs a kind.')
    if config['kind'] not in ['slack-sink']:
        raise TypeError('Unsupported Camel sink.')
    if 'channel' not in config:
        raise TypeError('Kind slack-sink requires a channel.')
    if 'webhookUrl' not in config:
        raise TypeError('Kind slack-sink requires a webhookUrl.')
    channel = config['channel']
    webhookUrl = config['webhookUrl']

    return [{
        'from': {
            'uri': endpoint,
            'steps': [{
                'to': f'slack:{channel}?webhookUrl={webhookUrl}',
            }]
        }
    }]
