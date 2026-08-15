-- Nebula Launcher Lumen Customization - Styles
-- Injects Nebula color scheme and branding into Lumen UI

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

local M = {}

function M.apply_nebula_theme()
    local style = require("style")
    
    -- Override default colors
    style.colors = {
        background = NEBULA_COLORS.bg,
        surface = NEBULA_COLORS.card_bg,
        border = NEBULA_COLORS.border,
        primary = NEBULA_COLORS.primary,
        primary_hover = NEBULA_COLORS.primary_hover,
        success = NEBULA_COLORS.success,
        warning = NEBULA_COLORS.warning,
        danger = NEBULA_COLORS.danger,
        text = NEBULA_COLORS.text,
        text_muted = NEBULA_COLORS.text_muted,
        accent = NEBULA_COLORS.accent,
    }
    
    -- Update component styles
    style.button = {
        primary = {
            background = NEBULA_COLORS.primary,
            hover = NEBULA_COLORS.primary_hover,
            text = "#FFFFFF",
            radius = 6,
        },
        secondary = {
            background = NEBULA_COLORS.card_bg,
            hover = NEBULA_COLORS.border,
            text = NEBULA_COLORS.text,
            border = NEBULA_COLORS.border,
            radius = 6,
        },
        danger = {
            background = NEBULA_COLORS.danger,
            hover = "#FF6B6B",
            text = "#FFFFFF",
            radius = 6,
        },
        success = {
            background = NEBULA_COLORS.success,
            hover = "#5FC670",
            text = "#FFFFFF",
            radius = 6,
        },
    }
    
    style.input = {
        background = NEBULA_COLORS.bg,
        border = NEBULA_COLORS.border,
        focus_border = NEBULA_COLORS.primary,
        text = NEBULA_COLORS.text,
        placeholder = NEBULA_COLORS.text_muted,
        radius = 4,
    }
    
    style.panel = {
        background = NEBULA_COLORS.card_bg,
        border = NEBULA_COLORS.border,
        radius = 8,
    }
    
    style.list = {
        background = NEBULA_COLORS.card_bg,
        border = NEBULA_COLORS.border,
        hover = NEBULA_COLORS.border,
        selected = NEBULA_COLORS.primary,
        radius = 6,
    }
    
    style.scrollbar = {
        track = NEBULA_COLORS.bg,
        thumb = NEBULA_COLORS.border,
        hover = NEBULA_COLORS.text_muted,
        radius = 4,
    }
    
    style.tab_bar = {
        background = NEBULA_COLORS.card_bg,
        border = NEBULA_COLORS.border,
        active_background = NEBULA_COLORS.primary,
        active_text = "#FFFFFF",
        inactive_text = NEBULA_COLORS.text_muted,
        radius = 4,
    }
    
    style.dialog = {
        background = NEBULA_COLORS.card_bg,
        border = NEBULA_COLORS.border,
        title_text = NEBULA_COLORS.text,
        radius = 10,
    }
    
    style.notification = {
        success_background = NEBULA_COLORS.success,
        error_background = NEBULA_COLORS.danger,
        warning_background = NEBULA_COLORS.warning,
        info_background = NEBULA_COLORS.primary,
        text = "#FFFFFF",
        radius = 8,
    }
    
    -- Apply styles
    style.apply()
end

function M.get_nebula_logo_path()
    -- Returns path to Nebula logo asset
    -- This will be overridden by PluginManager during installation
    return "assets/lumen/logo.png"
end

function M.get_nebula_logo_small_path()
    return "assets/lumen/logo-small.png"
end

-- Auto-apply theme when module loads
M.apply_nebula_theme()

return M