// MongoDB Initialization Script
// Creates indexes and initial configuration

db = db.getSiblingDB('picam');

// Create collections with validation
db.createCollection('operational_data', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['timestamp', 'location_id', 'location_type'],
      properties: {
        timestamp: { bsonType: 'date' },
        location_id: { bsonType: 'string' },
        location_type: { bsonType: 'string' },
        arrival_count: { bsonType: 'int', minimum: 0 },
        departure_count: { bsonType: 'int', minimum: 0 },
        queue_length: { bsonType: 'int', minimum: 0 }
      }
    }
  }
});

db.createCollection('daily_insights');
db.createCollection('roi_log');
db.createCollection('action_recommendations');
db.createCollection('calculation_audit_log');
db.createCollection('system_configuration');
db.createCollection('video_processing_log');

// Create indexes
db.operational_data.createIndex({ timestamp: -1, location_id: 1 });
db.operational_data.createIndex({ date: -1 });
db.operational_data.createIndex({ location_id: 1, date: -1 });

db.daily_insights.createIndex({ date: -1 }, { unique: true });

db.roi_log.createIndex({ timestamp: -1 });
db.roi_log.createIndex({ entry_hash: 1 }, { unique: true });
db.roi_log.createIndex({ sequence_number: -1 });

db.action_recommendations.createIndex({ date: -1, location_id: 1 });
db.action_recommendations.createIndex({ status: 1 });

db.calculation_audit_log.createIndex({ calculation_type: 1, timestamp: -1 });

print('PICAM MongoDB initialization complete');