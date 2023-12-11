rem aws timestream-write describe-table --database-name timestream-salmon-metrics-events-storage-devam --table-name tstable-salmon-glue-metrics-devam

aws timestream-write delete-table --database-name timestream-salmon-metrics-events-storage-devam --table-name tstable-salmon-glue-metrics-devam

aws timestream-write create-table --database-name timestream-salmon-metrics-events-storage-devam --table-name tstable-salmon-glue-metrics-devam ^
 --retention-properties MemoryStoreRetentionPeriodInHours=24,MagneticStoreRetentionPeriodInDays=365