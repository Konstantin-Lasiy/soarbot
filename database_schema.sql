-- Supabase database schema for SoarBot user configurations (v2)
-- Supports multiple wind stations per user

-- Users table (unchanged)
CREATE TABLE users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    telegram_chat_id VARCHAR(50) UNIQUE NOT NULL,
    username VARCHAR(100),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Wind stations table - catalog of available stations
CREATE TABLE wind_stations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    station_id VARCHAR(20) UNIQUE NOT NULL, -- e.g., 'FPS', 'KSLC', etc.
    name VARCHAR(100) NOT NULL,
    description TEXT,
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    elevation_ft INTEGER,
    timezone VARCHAR(50) DEFAULT 'America/Denver',
    api_provider VARCHAR(50) DEFAULT 'synoptic', -- 'synoptic', 'weather_underground', etc.
    api_config JSONB, -- provider-specific config like tokens, endpoints
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User global preferences (notification settings that apply across all stations)
CREATE TABLE user_preferences (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- Global notification settings
    notification_cooldown_hours INTEGER DEFAULT 4,
    timezone VARCHAR(50) DEFAULT 'America/Denver',
    notifications_enabled BOOLEAN DEFAULT true,
    
    -- Message preferences
    include_weather_chart BOOLEAN DEFAULT false,
    message_rows INTEGER DEFAULT 6,
    message_format VARCHAR(20) DEFAULT 'html', -- 'html', 'markdown', 'plain'
    
    -- Time preferences
    enable_winter_midday BOOLEAN DEFAULT true,
    quiet_hours_start TIME, -- e.g., '22:00'
    quiet_hours_end TIME,   -- e.g., '06:00'
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id)
);

-- User station configurations - specific settings for each station a user monitors
CREATE TABLE user_station_configs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    station_id UUID REFERENCES wind_stations(id) ON DELETE CASCADE,
    
    -- Station-specific wind conditions
    wind_speed_min DECIMAL(4,1) DEFAULT 8.5,
    wind_speed_max DECIMAL(4,1) DEFAULT 16.0,
    wind_direction_min INTEGER DEFAULT 130,
    wind_direction_max INTEGER DEFAULT 180,
    
    -- Gust settings
    max_gust_differential DECIMAL(4,1) DEFAULT 5.0,
    
    -- Station priority and customization
    priority INTEGER DEFAULT 1, -- 1=highest priority for this user
    custom_name VARCHAR(100), -- user's custom name for this station
    is_enabled BOOLEAN DEFAULT true,
    
    -- Station-specific conditions
    min_visibility_miles DECIMAL(4,1), -- optional visibility requirement
    max_precipitation_rate DECIMAL(4,2), -- mm/hr
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, station_id)
);

-- Notification history (updated to include station info)
CREATE TABLE notification_history (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    station_id UUID REFERENCES wind_stations(id) ON DELETE SET NULL,
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    message_content TEXT,
    conditions_met JSONB, -- which conditions were met
    station_data JSONB, -- raw weather data snapshot
    notification_type VARCHAR(50) DEFAULT 'conditions_met' -- 'conditions_met', 'weather_alert', 'test'
);

-- Insert default wind stations
INSERT INTO wind_stations (station_id, name, description, latitude, longitude, elevation_ft, timezone, api_provider, api_config) VALUES
('FPS', 'South Side Flight Park', 'Primary soaring site in Utah', 40.5247, -111.8638, 4500, 'America/Denver', 'synoptic', '{"lookback_minutes": 120}'),
('KSLC', 'Salt Lake City International', 'SLC Airport weather station', 40.7899, -111.9791, 4227, 'America/Denver', 'synoptic', '{"lookback_minutes": 60}'),
('KOGD', 'Ogden-Hinckley Airport', 'Northern Utah weather station', 41.1958, -112.0119, 4473, 'America/Denver', 'synoptic', '{"lookback_minutes": 60}');

-- Indexes for performance
CREATE INDEX idx_users_telegram_chat_id ON users(telegram_chat_id);
CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);
CREATE INDEX idx_user_station_configs_user_id ON user_station_configs(user_id);
CREATE INDEX idx_user_station_configs_station_id ON user_station_configs(station_id);
CREATE INDEX idx_user_station_configs_enabled ON user_station_configs(is_enabled) WHERE is_enabled = true;
CREATE INDEX idx_notification_history_user_id ON notification_history(user_id);
CREATE INDEX idx_notification_history_sent_at ON notification_history(sent_at);
CREATE INDEX idx_notification_history_station_id ON notification_history(station_id);
CREATE INDEX idx_wind_stations_active ON wind_stations(is_active) WHERE is_active = true;

-- Row Level Security (RLS)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_station_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE wind_stations ENABLE ROW LEVEL SECURITY;

-- RLS Policies
-- Users can only access their own data
CREATE POLICY "Users can view own profile" ON users FOR SELECT USING (auth.uid()::text = id::text);
CREATE POLICY "Users can update own profile" ON users FOR UPDATE USING (auth.uid()::text = id::text);

CREATE POLICY "Users can manage own preferences" ON user_preferences FOR ALL USING (
    user_id IN (SELECT id FROM users WHERE auth.uid()::text = id::text)
);

CREATE POLICY "Users can manage own station configs" ON user_station_configs FOR ALL USING (
    user_id IN (SELECT id FROM users WHERE auth.uid()::text = id::text)
);

CREATE POLICY "Users can view own notifications" ON notification_history FOR SELECT USING (
    user_id IN (SELECT id FROM users WHERE auth.uid()::text = id::text)
);

-- Wind stations are readable by all authenticated users
CREATE POLICY "Authenticated users can view wind stations" ON wind_stations FOR SELECT TO authenticated USING (true);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;   
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_preferences_updated_at BEFORE UPDATE ON user_preferences FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_station_configs_updated_at BEFORE UPDATE ON user_station_configs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_wind_stations_updated_at BEFORE UPDATE ON wind_stations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Views for convenience

-- View to get all user configurations with station details
CREATE VIEW user_configurations_with_stations AS
SELECT 
    u.id as user_id,
    u.telegram_chat_id,
    u.username,
    u.first_name,
    u.last_name,
    up.notification_cooldown_hours,
    up.timezone,
    up.notifications_enabled,
    up.include_weather_chart,
    up.message_rows,
    up.enable_winter_midday,
    up.quiet_hours_start,
    up.quiet_hours_end,
    ws.station_id,
    ws.name as station_name,
    ws.description as station_description,
    ws.latitude,
    ws.longitude,
    ws.elevation_ft,
    ws.api_provider,
    ws.api_config,
    usc.wind_speed_min,
    usc.wind_speed_max,
    usc.wind_direction_min,
    usc.wind_direction_max,
    usc.max_gust_differential,
    usc.priority,
    usc.custom_name,
    usc.is_enabled as station_enabled,
    usc.min_visibility_miles,
    usc.max_precipitation_rate
FROM users u
JOIN user_preferences up ON u.id = up.user_id
JOIN user_station_configs usc ON u.id = usc.user_id
JOIN wind_stations ws ON usc.station_id = ws.id
WHERE u.is_active = true 
  AND up.notifications_enabled = true 
  AND usc.is_enabled = true 
  AND ws.is_active = true;

-- Function to create default preferences when a user is created
CREATE OR REPLACE FUNCTION create_default_user_preferences()
RETURNS TRIGGER AS $$
BEGIN
    -- Create default preferences
    INSERT INTO user_preferences (user_id) VALUES (NEW.id);
    
    -- Add default station configuration for FPS
    INSERT INTO user_station_configs (user_id, station_id, priority)
    SELECT NEW.id, ws.id, 1
    FROM wind_stations ws
    WHERE ws.station_id = 'FPS' AND ws.is_active = true;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to create default preferences
CREATE TRIGGER create_user_defaults_trigger
    AFTER INSERT ON users
    FOR EACH ROW
    EXECUTE FUNCTION create_default_user_preferences();