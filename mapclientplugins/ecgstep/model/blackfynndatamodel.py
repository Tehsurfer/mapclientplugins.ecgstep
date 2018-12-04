# blackfynndatamodel.py
# ---------------------
# BlackfynnDataModel is a class used to store API keys of users who log in and use them to access the
# blackfynn-python API. http://help.blackfynn.com/developer-tools

from blackfynn import Blackfynn
from natsort import natsorted


class BlackfynnDataModel(object):

    def __init__(self):
        self._settings = {'active-profile': ''}
        self._cache = {}
        self._bf = None

    def addProfile(self, profile):
        self._settings[profile['name']] = {'api_token': profile['token'], 'api_secret': profile['secret']}

    def setActiveProfile(self, profile_name):
        self._settings['active-profile'] = profile_name

    def getActiveProfile(self):
        return self._settings['active-profile']

    def getExistingProfileNames(self):
        profile_names = self._settings.keys()
        profile_names.remove('active-profile')
        return profile_names

    def _getBlackfynn(self, profile_name):
        api_key = self._settings[profile_name]['api_token']
        api_secret = self._settings[profile_name]['api_secret']
        # print('[{0}]:[{1}]'.format(api_key, api_secret))
        self._bf = Blackfynn(api_token=api_key, api_secret=api_secret)
        return self._bf

    def getDatasets(self, profile_name, refresh=False):
        if profile_name in self._cache and not refresh:
            datasets = self._cache[profile_name]['datasets']
        elif refresh:
            bf = self._getBlackfynn(profile_name)
            datasets = bf.datasets()
            if profile_name in self._cache:
                self._cache[profile_name]['datasets'] = datasets
            else:
                self._cache[profile_name] = {'datasets': datasets}
        else:
            datasets = []

        return datasets

    def getDataset(self, profile_name, dataset_name, refresh=False):
        if profile_name in self._cache and dataset_name in self._cache[profile_name] and not refresh:
            dataset = self._cache[profile_name][dataset_name]
        elif refresh:
            bf = self._getBlackfynn(profile_name)
            dataset = bf.get_dataset(dataset_name)
            self._cache[profile_name][dataset_name] = dataset
        else:
            dataset = []

        return dataset

    def getTimeseriesData(self, profile_name, dataset_name, timeseries_name, length):
        for stored_dataset in self._cache[profile_name][dataset_name]:
            if stored_dataset.name == timeseries_name:
                if stored_dataset.type == 'TimeSeries':
                    return  self.proecessTimeseriesData(stored_dataset, length)
                if stored_dataset.type == 'Tabular':
                    return  self.proecessTabularData(stored_dataset, length)

    def proecessTimeseriesData(self, stored_dataset, length):
        timeseries_dframe = stored_dataset.get_data(length='{0}s'.format(length))
        cache_output = self._create_file_cache(timeseries_dframe)
        absolute_timeseries_values = timeseries_dframe.axes[0]
        relative_times = []
        for time in absolute_timeseries_values:
            relative_times.append(round(time.timestamp() - absolute_timeseries_values[0].timestamp(), 6))
        return [cache_output, relative_times]

    def proecessTabularData(self, stored_dataset, length):
        timeseries_dframe =stored_dataset.get_data(length*100)

        absolute_timeseries_values = timeseries_dframe.axes[0]
        relative_times = []
        if str(type(absolute_timeseries_values[0])) == "<class 'pandas._libs.tslibs.timestamps.Timestamp'>":
            for time in absolute_timeseries_values:
                relative_times.append(round(time.timestamp() - absolute_timeseries_values[0].timestamp(), 6))
        else:
            for time in absolute_timeseries_values:
                relative_times.append(time)

        cache_output = self._create_file_cache(timeseries_dframe)
        return [cache_output, relative_times]

    def _create_file_cache(self, data_frame):

        cache_dictionary = {}
        keys = natsorted(data_frame.keys()) # Sort the keys in 'natural' order
        for key in keys:
            if 'time' not in key:
                cache_dictionary[key] = data_frame[key].values.tolist()

        return cache_dictionary

    def uploadRender(self, filePath):
        # uploadRender: Takes a given file path and uploads it to blackfynn in a folder called 'Zinc Exports' for the
        #               user currently logged in.
        try:
            ds = self._bf.get_dataset('Zinc Exports')
        except:
            self._bf.create_dataset('Zinc Exports')
            ds = self._bf.get_dataset('Zinc Exports')
        ds.upload(filePath)

    def getSettings(self):
        return self._settings

    def setSettings(self, settings):
        print('set settings {0}',format(settings))
        self._settings.update(settings)
