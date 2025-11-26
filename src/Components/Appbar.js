import React from "react";
import {
    Box,
    AppBar,
    Toolbar,
    IconButton,
    Typography,
    Tabs,
    Tab,
    Container,
    List,
    ListItem,
    ListItemAvatar,
    Avatar,
    ListItemText,
    Divider,
    Grid,
    useTheme,
    useMediaQuery,
    Badge,
} from "@mui/material";
import FilterAltIcon from '@mui/icons-material/FilterAlt';
import MenuIcon from "@mui/icons-material/Menu";
import FilterListIcon from "@mui/icons-material/FilterList";



export const TopBar = () => {
    const [tab, setTab] = React.useState(1);
    return (
        <AppBar
            position="sticky"
            elevation={0}
            maxWidth="sm"
            sx={{

                bgcolor: "transparent",
                borderBottom: "1px solid rgba(255,255,255,0.06)",
            }}
        >
            <Toolbar sx={{ px: { xs: 1, sm: 2 } ,display:"flex",justifyContent:"space-between"}}>
                <IconButton edge="start" sx={{ color: "#fff", mr: 1 }}>
                    <MenuIcon />
                </IconButton>

                <IconButton sx={{ color: "#fff" }}>
                    <FilterAltIcon />
                </IconButton>
            </Toolbar>

            <Tabs
                value={tab}
                onChange={(_, v) => setTab(v)}
                variant="scrollable"
                scrollButtons="auto"
                sx={{
                    bgcolor: "#0b0b0b",
                    ".MuiTabs-indicator": { backgroundColor: "transparent" },
                    px: 0,
                }}
            >
                {["Favourites", "Forex", "Crypto", "Indices", "Derivatives"].map(
                    (label, index) => (
                        <Tab
                            key={index}
                            label={label}
                            sx={{
                                textTransform: "none",
                                fontWeight: tab === index ? 700 : 500,
                                color: tab === index ? "#fff" : "rgba(255,255,255,0.35)",

                                // 👇 HOVER EFFECT
                                "&:hover": {
                                    color: "#fff",
                                },

                                // 👇 WHEN ACTIVE (CLICK)
                                "&.Mui-selected": {
                                    color: "#fff",
                                    fontWeight: 700,
                                },
                            }}
                        />
                    )
                )}
            </Tabs>

        </AppBar>
    )


}
