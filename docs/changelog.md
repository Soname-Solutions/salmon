# Changelog

All notable changes to this project will be documented in this file.

## 1.0.0 ({release_date})


### Features

* **Unit Tests:** Improved tests coverage. ([13aa12b](https://github.com/Soname-Solutions/salmon/commit/13aa12bbe7bf8af70f880863e3bfb8ad19349399))
* **Lambda:** Added Digest Lambda. Required for distributing daily Digest. ([c1b70a6](https://github.com/Soname-Solutions/salmon/commit/c1b70a66da2b8f845665ae1b76bd426334240d5e))
* **Stack:** Introduced Grafana stack. This enables launching Grafana instance with default provisioning dashboards based on Timestream tables and Cloudwatch log groups. ([b64a94c](https://github.com/Soname-Solutions/salmon/commit/b64a94c0cf97a8f44d8e6d110882cca2a1b7970e))
* **Cloudwatch:** Added functionality to publish alerting events to Cloudwatch log groups. ([b9f4535](https://github.com/Soname-Solutions/salmon/commit/b9f45358082c586af22cd494b6adf3867675251d))
* **Lambda:** Added orchestration and extract metrics Lambdas. Required for extracting metric information (data since the last update) for all resources and saving this data to Timestream database. ([fb17509](https://github.com/Soname-Solutions/salmon/commit/fb1750996059cff7e1935dde6fa32360696f1215))
* **Event Mappers:** Added functionality for event mappers. Designed to map AWS events to notification messages. ([b153add](https://github.com/Soname-Solutions/salmon/commit/b153add530ab52b9a9006ca416033311168ca72a))
* **AWS Naming Convention:** Included a naming convention for AWS resources to be created. ([6b2a45d](https://github.com/Soname-Solutions/salmon/commit/6b2a45d4402658a412cadacb43f0dca7dd3f4cd2))
* **Lambda:** Added Alerting Lambda. Required for notifying on failed events. ([0a12c7d](https://github.com/Soname-Solutions/salmon/commit/0a12c7dc4786c8724ced3c0d8c01d397b44efd8f))
* **Lambda:** Added Notification Lambda. Required for sending messages via provided delivery method. ([08d4d37](https://github.com/Soname-Solutions/salmon/commit/08d4d37db0f0e7ad8562767117289289849d499c))
* **Settings:** Added a Settings validation module. This validates the settings before creating any resources. ([b1b143b](https://github.com/Soname-Solutions/salmon/commit/b1b143ba2fc89eaa13bc360e67799eba5eb83edf))
* **Stack:** Introduced Monitoring stack. Required for provisioning extract metrics and digest Lambdas, as well as Timestream tables. ([0c147f6](https://github.com/Soname-Solutions/salmon/commit/0c147f68594937f3ad3c46c15f422d017d00a5a4))
* **Stack:** Introduced Monitored stack. Required for creating cross-account roles to monitor resources across various AWS accounts and regions centrally. ([adfa27](https://github.com/Soname-Solutions/salmon/commit/adfa27ceae1f182e09c44245beb8894fe4575c0c))
* **Stack:** Introduced Alerting stack. Required for provisioning the needed resources to catch and process alerting events. ([bb547fb](https://github.com/Soname-Solutions/salmon/commit/bb547fb725169bd1dc5d488740e316e40d40fc64))
* **Settings:** Added main functionality for Settings. ([8bf9e4d](https://github.com/Soname-Solutions/salmon/commit/8bf9e4de391a9928e56a589e26702d9eacaf286c))
* **Stack:** Introduced Tooling Common stack. Required for provisioning common Salmon components (such as metrics history database, notification service, alerts processing and settings components). ([15764c4](https://github.com/Soname-Solutions/salmon/commit/15764c4318466bb158497bf57af479574f6e0ecf))