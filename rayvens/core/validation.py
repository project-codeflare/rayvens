from collections import namedtuple

# Keep track of the Stream components of interest:
# - the name of the stream;
# - the list of sources attached to the stream;
# - the list of sinks attached to the stream.
StreamMetadata = namedtuple('StreamMetadata', 'name sources sinks')


class Validation:
    def __init__(self):
        self._stream_metadata = {}

    def add_stream(self, stream, name):
        self._stream_metadata[str(stream)] = StreamMetadata(name, [], [])

    def validate_stream(self, stream):
        # Check add source is valid.
        if str(stream) not in self._stream_metadata:
            raise RuntimeError('Attempt to use unknown stream.')

    def get_stream_name(self, stream):
        self.validate_stream(stream)
        return self._stream_metadata[str(stream)].name

    def add_source(self, stream, source_name):
        self.validate_stream(stream)
        self._stream_metadata[str(stream)].sources.append(source_name)

    def add_sink(self, stream, sink_name):
        self.validate_stream(stream)
        self._stream_metadata[str(stream)].sinks.append(sink_name)

    def get_sources(self, stream):
        return self._stream_metadata[str(stream)].sources

    def get_sinks(self, stream):
        return self._stream_metadata[str(stream)].sinks

    def validate_integration(self, integration_name):
        # Check integration is attached to a stream.
        valid_integration = False
        for str_stream in self._stream_metadata:
            if integration_name in self._stream_metadata[str_stream].sources:
                valid_integration = True
                break
            if integration_name in self._stream_metadata[str_stream].sinks:
                valid_integration = True
                break

        if not valid_integration:
            raise RuntimeError(f'{integration_name} not attached to a stream')
