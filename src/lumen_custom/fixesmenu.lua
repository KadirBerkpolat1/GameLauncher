-- Nebula Launcher Lumen Customization
-- This file replaces the default fixesmenu.lua to add Nebula Fixes tab

local api = require("api")
local config = require("config")
local utils = require("utils")
local ui = require("ui")

local M = {}

-- Nebula color scheme
local NEBULA_COLORS = {
    bg = "#0D1117",
    card_bg = "#161B22",
    border = "#30363D",
    primary = "#58A6FF",
    primary_hover = "#79C0FF",
    success = "#3FB950",
    warning = "#D29922",
    danger = "#F85149",
    text = "#E6EDF3",
    text_muted = "#8B949E",
    accent = "#A371F7",
}

-- Nebula fix providers (matching launcher's provider registry)
local NEBULA_PROVIDERS = {
    {
        id = "ryuu",
        name = "Ryuu",
        description = "Official Ryuu API fixes with Online/Bypass badges",
        badges = {"Online", "Bypass"},
        requires_auth = true,
    },
    {
        id = "crackbypass",
        name = "CrackBypass (CrakFiles)",
        description = "Crack fixes from CrakFiles with buzzheavier downloads",
        badges = {"Crack", "Online Fix", "Bypass", "DLC Unlocker"},
        requires_auth = false,
    },
    {
        id = "onlinefix",
        name = "OnlineFix",
        description = "Multiplayer fixes from online-fix.me",
        badges = {"Online"},
        requires_auth = false,
    },
    {
        id = "freetp",
        name = "FreeTP",
        description = "Multiplayer fixes from freetp.org",
        badges = {"Online"},
        requires_auth = false,
    },
    {
        id = "goldberg",
        name = "Goldberg Steam Emulator",
        description = "Offline singleplayer DRM removal",
        badges = {"Offline"},
        requires_auth = false,
    },
}

function M.create_fixes_menu()
    local window = ui.create_window("Nebula Fixes", 800, 600)
    window:set_background(NEBULA_COLORS.bg)
    
    -- Header with Nebula branding
    local header = ui.create_panel(window, 800, 80)
    header:set_position(0, 0)
    header:set_background(NEBULA_COLORS.card_bg)
    header:set_border(1, NEBULA_COLORS.border)
    
    local logo = ui.create_label(header, "🌌 Nebula Fixes")
    logo:set_position(20, 15)
    logo:set_font_size(24)
    logo:set_color(NEBULA_COLORS.primary)
    logo:set_bold(true)
    
    local subtitle = ui.create_label(header, "Multi-source fix manager for Steam games")
    subtitle:set_position(20, 50)
    subtitle:set_font_size(12)
    subtitle:set_color(NEBULA_COLORS.text_muted)
    
    -- Provider tabs
    local tab_bar = ui.create_tab_bar(window, 800, 40)
    tab_bar:set_position(0, 85)
    tab_bar:set_background(NEBULA_COLORS.card_bg)
    tab_bar:set_border(1, NEBULA_COLORS.border)
    
    for _, provider in ipairs(NEBULA_PROVIDERS) do
        local badge_text = ""
        for i, badge in ipairs(provider.badges) do
            badge_text = badge_text .. " [" .. badge .. "]"
        end
        
        local tab_name = provider.name .. badge_text
        local tab = tab_bar:add_tab(tab_name)
        tab:set_data("provider_id", provider.id)
        tab:set_data("provider_data", provider)
    end
    
    -- Content area
    local content = ui.create_scroll_panel(window, 780, 450)
    content:set_position(10, 135)
    content:set_background(NEBULA_COLORS.bg)
    
    -- Search bar
    local search_panel = ui.create_panel(content, 760, 50)
    search_panel:set_position(10, 10)
    search_panel:set_background(NEBULA_COLORS.card_bg)
    search_panel:set_border(1, NEBULA_COLORS.border)
    search_panel:set_radius(6)
    
    local search_label = ui.create_label(search_panel, "Search Game:")
    search_label:set_position(15, 15)
    search_label:set_color(NEBULA_COLORS.text_muted)
    
    local search_input = ui.create_input(search_panel, 400, 30)
    search_input:set_position(120, 10)
    search_input:set_placeholder("Enter game name...")
    search_input:set_background(NEBULA_COLORS.bg)
    search_input:set_border(1, NEBULA_COLORS.border)
    search_input:set_color(NEBULA_COLORS.text)
    search_input:set_radius(4)
    
    local search_btn = ui.create_button(search_panel, "Search", 100, 30)
    search_btn:set_position(540, 10)
    search_btn:set_background(NEBULA_COLORS.primary)
    search_btn:set_color("#FFFFFF")
    search_btn:set_radius(4)
    
    -- Results list
    local results_list = ui.create_list(content, 760, 370)
    results_list:set_position(10, 70)
    results_list:set_background(NEBULA_COLORS.card_bg)
    results_list:set_border(1, NEBULA_COLORS.border)
    results_list:set_radius(6)
    
    -- Current provider state
    local current_provider = NEBULA_PROVIDERS[1]
    local current_query = ""
    
    -- Search function
    local function do_search(query, provider_id)
        current_query = query
        current_provider = nil
        for _, p in ipairs(NEBULA_PROVIDERS) do
            if p.id == provider_id then
                current_provider = p
                break
            end
        end
        
        if not current_provider then
            current_provider = NEBULA_PROVIDERS[1]
        end
        
        -- Show loading
        results_list:clear()
        local loading = results_list:add_item("Searching " .. current_provider.name .. "...")
        loading:set_color(NEBULA_COLORS.text_muted)
        
        -- Call backend API
        api.search_fixes(query, provider_id, function(success, data)
            results_list:clear()
            
            if not success then
                local err = results_list:add_item("Error: " .. (data or "Unknown error"))
                err:set_color(NEBULA_COLORS.danger)
                return
            end
            
            if not data or #data == 0 then
                local none = results_list:add_item("No fixes found for '" .. query .. "' on " .. current_provider.name)
                none:set_color(NEBULA_COLORS.text_muted)
                return
            end
            
            for _, fix in ipairs(data) do
                local item = results_list:add_item("")
                item:set_height(80)
                item:set_data("fix_data", fix)
                
                -- Fix title
                local title = ui.create_label(item, fix.title or "Unknown Fix")
                title:set_position(15, 5)
                title:set_font_size(14)
                title:set_bold(true)
                title:set_color(NEBULA_COLORS.text)
                
                -- Version and source
                local meta = ui.create_label(item, "v" .. (fix.version or "1.0.0") .. " | " .. current_provider.name)
                meta:set_position(15, 30)
                meta:set_font_size(11)
                meta:set_color(NEBULA_COLORS.text_muted)
                
                -- Badges
                local badge_x = 15
                for _, badge in ipairs(fix.badges or {}) do
                    local badge_label = ui.create_label(item, "[" .. badge .. "]")
                    badge_label:set_position(badge_x, 55)
                    badge_label:set_font_size(10)
                    badge_label:set_padding(6, 3)
                    badge_label:set_radius(3)
                    
                    if badge:lower():find("online") then
                        badge_label:set_background(NEBULA_COLORS.success)
                        badge_label:set_color("#FFFFFF")
                    elseif badge:lower():find("bypass") then
                        badge_label:set_background(NEBULA_COLORS.warning)
                        badge_label:set_color("#000000")
                    elseif badge:lower():find("crack") then
                        badge_label:set_background(NEBULA_COLORS.danger)
                        badge_label:set_color("#FFFFFF")
                    else
                        badge_label:set_background(NEBULA_COLORS.accent)
                        badge_label:set_color("#FFFFFF")
                    end
                    
                    badge_x = badge_x + badge_label:get_width() + 5
                end
                
                -- Apply button
                local apply_btn = ui.create_button(item, "Apply Fix", 100, 30)
                apply_btn:set_position(640, 25)
                apply_btn:set_background(NEBULA_COLORS.success)
                apply_btn:set_color("#FFFFFF")
                apply_btn:set_radius(4)
                apply_btn:set_data("fix_data", fix)
                apply_btn:set_data("provider_id", provider_id)
                
                apply_btn.on_click = function(btn)
                    local fix_data = btn:get_data("fix_data")
                    local prov_id = btn:get_data("provider_id")
                    
                    -- Show confirmation
                    local confirm = ui.create_confirm_dialog(
                        "Apply Fix",
                        "Apply '" .. fix_data.title .. "' from " .. current_provider.name .. "?\n\nThis will download and extract the fix to your game folder.\nLaunch options will be updated automatically (no Steam restart needed).",
                        function(confirmed)
                            if confirmed then
                                apply_fix(fix_data, prov_id)
                            end
                        end
                    )
                    confirm:show()
                end
            end
        end)
    end
    
    -- Apply fix function
    local function apply_fix(fix_data, provider_id)
        -- Show progress
        local progress = ui.create_progress_dialog("Applying Fix", "Downloading and extracting...")
        progress:show()
        
        api.download_and_apply_fix(fix_data, provider_id, function(stage, message)
            progress:set_message(message)
        end, function(success, result)
            progress:hide()
            
            if success then
                ui.show_notification("Fix Applied", "Fix applied successfully!\nLaunch options updated - no Steam restart needed!", "success")
                
                -- Refresh game list in main window
                api.refresh_game_list()
            else
                ui.show_notification("Fix Failed", "Failed to apply fix: " .. (result or "Unknown error"), "error")
            end
        end)
    end
    
    -- Tab change handler
    tab_bar.on_tab_change = function(tab)
        local provider_id = tab:get_data("provider_id")
        local provider_data = tab:get_data("provider_data")
        current_provider = provider_data
        
        if current_query and current_query ~= "" then
            do_search(current_query, provider_id)
        else
            results_list:clear()
            local hint = results_list:add_item("Enter a game name and click Search to find fixes from " .. provider_data.name)
            hint:set_color(NEBULA_COLORS.text_muted)
        end
    end
    
    -- Search button handler
    search_btn.on_click = function()
        local query = search_input:get_text()
        if query and query ~= "" then
            local active_tab = tab_bar:get_active_tab()
            local provider_id = active_tab:get_data("provider_id")
            do_search(query, provider_id)
        end
    end
    
    search_input.on_enter = function()
        search_btn:click()
    end
    
    -- Initialize with first tab
    tab_bar:set_active_tab(1)
    
    return window
end

-- Register with Lumen's menu system
local function register_nebula_fixes()
    local menu = require("menu")
    menu.register_tab("Nebula Fixes", M.create_fixes_menu, 3) -- Priority 3 (after Main, Settings)
end

-- Auto-register when loaded
register_nebula_fixes()

return M