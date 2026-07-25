from studio.terrain.srtm_provider import SRTMProvider

provider = SRTMProvider()

print(provider.elevation(46.089, 4.395))