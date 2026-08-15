-- Nebula Launcher Lumen Customization - SLS Menu Extension
-- Adds "Nebula Settings" entry to Lumen's SLS menu

local api = require("api")
local config = require("config")
local ui = require("ui")

local M = {}

local NEBULA_COLORS = {
    bg = "#0D1117",
    card_bg = "#161B22",
    border = "#30363D",
    primary = "#58A6FF",
    primary_hover = "#79C0FF",
    success = "#3FB950",
    text = "#E6EDF3",
    text_muted = "#8B949E",
}

function M.create_nebula_settings()
    local window = ui.create_window("Nebula Settings", 600, 500)
    window:set_background(NEBULA_COLORS.bg)
    
    -- Header
    local header = ui.create_panel(window, 600, 70)
    header:set_position(0, 0)
    header:set_background(NEBULA_COLORS.card_bg)
    header:set_border(1, NEBULA_COLORS.border)
    
    local title = ui.create_label(header, "🌌 Nebula Launcher Settings")
    title:set_position(20, 15)
    title:set_font_size(20)
    title:set_color(NEBULA_COLORS.primary)
    title:set_bold(true)
    
    local subtitle = ui.create_label(header, "Configure fix providers, CloudRedirect, and Steam integration")
    subtitle:set_position(20, 45)
    subtitle:set_font_size(11)
    subtitle:set_color(NEBULA_COLORS.text_muted)
    
    -- Content scroll panel
    local content = ui.create_scroll_panel(window, 560, 400)
    content:set_position(20, 80)
    content:set_background(NEBULA_COLORS.bg)
    
    y_pos = 10
    
    -- Section: Fix Provider Priority
    local section1 = ui.create_panel(content, 540, 200)
    section1:set_position(10, y_pos)
    section1:set_background(NEBULA_COLORS.card_bg)
    section1:set_border(1, NEBULA_COLORS.border)
    section1:set_radius(8)
    
    local sec1_title = ui.create_label(section1, "Fix Provider Priority")
    sec1_title:set_position(15, 15)
    sec1_title:set_font_size(14)
    sec1_title:set_bold(true)
    sec1_title:set_color(NEBULA_COLORS.text)
    
    local sec1_desc = ui.create_label(section1, "Drag to reorder - higher priority providers are searched first")
    sec1_desc:set_position(15, 40)
    sec1_desc:set_font_size(11)
    sec1_desc:set_color(NEBULA_COLORS.text_muted)
    
    -- Provider list (read-only in Lumen, configured in launcher)
    local providers = {
        {id = "ryuu", name = "Ryuu", badges = {"Online", "Bypass"}, enabled = true},
        {id = "crackbypass", name = "CrackBypass (CrakFiles)", badges = {"Crack", "Online Fix", "Bypass"}, enabled = true},
        {id = "onlinefix", name = "OnlineFix", badges = {"Online"}, enabled = true},
        {id = "freetp", name = "FreeTP", badges = {"Online"}, enabled = true},
        {id = "goldberg", name = "Goldberg Steam Emulator", badges = {"Offline"}, enabled = true},
    }
    
    local list_y = 70
    for i, p in ipairs(providers) do
        local item = ui.create_panel(section1, 510, 28)
        item:set_position(15, list_y)
        item:set_background(NEBULA_COLORS.bg)
        item:set_border(1, NEBULA_COLORS.border)
        item:set_radius(4)
        
        local num = ui.create_label(item, tostring(i) .. ".")
        num:set_position(10, 5)
        num:set_font_size(12)
        num:set_color(NEBULA_COLORS.primary)
        
        local name = ui.create_label(item, p.name)
        name:set_position(35, 5)
        name:set_font_size(12)
        name:set_color(NEBULA_COLORS.text)
        
        local badge_x = 35 + name:get_width() + 10
        for _, badge in ipairs(p.badges) do
            local b = ui.create_label(item, "[" .. badge .. "]")
            b:set_position(badge_x, 3)
            b:set_font_size(9)
            b:set_padding(4, 2)
            b:set_radius(3)
            if badge:lower():find("online") then
                b:set_background(NEBULA_COLORS.success)
                b:set_color("#FFFFFF")
            elseif badge:lower():find("bypass") then
                b:set_background(NEBULA_COLORS.warning)
                b:set_color("#000000")
            else
                b:set_background(NEBULA_COLORS.primary)
                b:set_color("#FFFFFF")
            end
            badge_x = badge_x + b:get_width() + 5
        end
        
        list_y = list_y + 32
    end
    
    y_pos = y_pos + 220
    
    -- Section: CloudRedirect
    local section2 = ui.create_panel(content, 540, 150)
    section2:set_position(10, y_pos)
    section2:set_background(NEBULA_COLORS.card_bg)
    section2:set_border(1, NEBULA_COLORS.border)
    section2:set_radius(8)
    
    local sec2_title = ui.create_label(section2, "☁ CloudRedirect")
    sec2_title:set_position(15, 15)
    sec2_title:set_font_size(14)
    sec2_title:set_bold(true)
    sec2_title:set_color(NEBULA_COLORS.text)
    
    local cloud_status = config.get("cloudredirect_enabled") or false
    local cloud_status_label = ui.create_label(section2, "Status: " .. (cloud_status and "Enabled" or "Disabled"))
    cloud_status_label:set_position(15, 45)
    cloud_status_label:set_font_size(12)
    cloud_status_label:set_color(cloud_status and NEBULA_COLORS.success or NEBULA_COLORS.text_muted)
    
    local cloud_btn = ui.create_button(section2, cloud_status and "Disable" or "Enable", 100, 30)
    cloud_btn:set_position(15, 80)
    cloud_btn:set_background(cloud_status and NEBULA_COLORS.danger or NEBULA_COLORS.success)
    cloud_btn:set_color("#FFFFFF")
    cloud_btn:set_radius(4)
    
    cloud_btn.on_click = function()
        local new_status = not cloud_status
        config.set("cloudredirect_enabled", new_status)
        api.toggle_cloudredirect(new_status)
        cloud_status_label:set_text("Status: " .. (new_status and "Enabled" or "Disabled"))
        cloud_status_label:set_color(new_status and NEBULA_COLORS.success or NEBULA_COLORS.text_muted)
        cloud_btn:set_text(new_status and "Disable" or "Enable")
        cloud_btn:set_background(new_status and NEBULA_COLORS.danger or NEBULA_COLORS.success)
        cloud_status = new_status
    end
    
    local cloud_provider = config.get("cloudredirect_provider") or "local"
    local provider_label = ui.create_label(section2, "Provider: " .. cloud_provider)
    provider_label:set_position(130, 85)
    provider_label:set_font_size(11)
    provider_label:set_color(NEBULA_COLORS.text_muted)
    
    y_pos = y_pos + 170
    
    -- Section: Steam Integration Mode
    local section3 = ui.create_panel(content, 540, 100)
    section3:set_position(10, y_pos)
    section3:set_background(NEBULA_COLORS.card_bg)
    section3:set_border(1, NEBULA_COLORS.border)
    section3:set_radius(8)
    
    local sec3_title = ui.create_label(section3, "Steam Integration Mode")
    sec3_title:set_position(15, 15)
    sec3_title:set_font_size(14)
    sec3_title:set_bold(true)
    sec3_title:set_color(NEBULA_COLORS.text)
    
    local mode = config.get("steam_integration_mode") or "classic"
    local mode_label = ui.create_label(section3, "Current: " .. (mode == "moon" and "Moon (slsteam-moon)" or "Classic (DepotDownloader)"))
    mode_label:set_position(15, 45)
    mode_label:set_font_size(11)
    mode_label:set_color(NEBULA_COLORS.text_muted)
    
    local mode_btn = ui.create_button(section3, "Open Launcher Settings", 180, 30)
    mode_btn:set_position(15, 70)
    mode_btn:set_background(NEBULA_COLORS.primary)
    mode_btn:set_color("#FFFFFF")
    mode_btn:set_radius(4)
    
    mode_btn.on_click = function()
        api.open_launcher_settings()
    end
    
    -- Bottom buttons
    local btn_row = ui.create_panel(window, 560, 50)
    btn_row:set_position(20, 440)
    btn_row:set_background(NEBULA_COLORS.bg)
    
    local close_btn = ui.create_button(btn_row, "Close", 100, 35)
    close_btn:set_position(460, 7)
    close_btn:set_background(NEBULA_COLORS.card_bg)
    close_btn:set_border(1, NEBULA_COLORS.border)
    close_btn:set_color(NEBULA_COLORS.text)
    close_btn:set_radius(6)
    
    close_btn.on_click = function()
        window:close()
    end
    
    return window
end

-- Register with Lumen's SLS menu
local function register_nebula_sls_settings()
    local slsmenu = require("slsmenu")
    slsmenu.register_entry("Nebula Settings", M.create_nebula_settings, {
        icon = "nebula",
        category = "Settings",
        priority = 10,
    })
end

-- Auto-register
register_nebula_sls_settings()

return M