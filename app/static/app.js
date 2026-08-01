// PadelFlow Frontend Application Logic
document.addEventListener("DOMContentLoaded", () => {
    let currentTournament = null;
    let tournamentsList = [];
    let currentAiGeneratedSpec = null;
    let originalPromptText = "";

    // Theme Toggle Logic (Light / Dark Mode)
    const themeBtn = document.getElementById("btn-theme-toggle");
    const themeIcon = document.getElementById("theme-toggle-icon");
    const themeText = document.getElementById("theme-toggle-text");

    function setTheme(theme) {
        document.documentElement.setAttribute("data-theme", theme);
        localStorage.setItem("padelflow_theme", theme);
        if (theme === "light") {
            if (themeIcon) themeIcon.textContent = "☀️";
            if (themeText) themeText.textContent = "Light";
        } else {
            if (themeIcon) themeIcon.textContent = "🌙";
            if (themeText) themeText.textContent = "Dark";
        }
    }

    const savedTheme = localStorage.getItem("padelflow_theme") || "dark";
    setTheme(savedTheme);

    themeBtn?.addEventListener("click", () => {
        const currentTheme = document.documentElement.getAttribute("data-theme") || "dark";
        const newTheme = currentTheme === "dark" ? "light" : "dark";
        setTheme(newTheme);
    });

    // Tab Switching
    const navItems = document.querySelectorAll(".nav-item");
    const tabContents = document.querySelectorAll(".tab-content");

    function switchTab(targetTab) {
        navItems.forEach(n => n.classList.remove("active"));
        tabContents.forEach(t => t.classList.remove("active"));

        const navBtn = document.querySelector(`.nav-item[data-tab="${targetTab}"]`);
        const tabEl = document.getElementById(`tab-${targetTab}`);

        if (navBtn) navBtn.classList.add("active");
        if (tabEl) tabEl.classList.add("active");

        if (targetTab === "tournaments") loadTournamentsList();
        if (targetTab === "matches") renderMatches();
        if (targetTab === "leaderboard") renderLeaderboard();
    }

    navItems.forEach(item => {
        item.addEventListener("click", () => switchTab(item.dataset.tab));
    });

    document.getElementById("btn-goto-ai-studio")?.addEventListener("click", () => switchTab("ai-studio"));
    document.getElementById("btn-view-full-leaderboard")?.addEventListener("click", () => switchTab("leaderboard"));

    // Modals Handling
    function setupModal(modalId, openBtnId) {
        const modal = document.getElementById(modalId);
        if (!modal) return;
        
        if (openBtnId) {
            const openBtn = document.getElementById(openBtnId);
            if (openBtn) openBtn.addEventListener("click", () => modal.classList.add("open"));
        }

        modal.querySelectorAll(".btn-close, .btn-close-modal").forEach(b => {
            b.addEventListener("click", () => modal.classList.remove("open"));
        });
    }

    setupModal("modal-tournament-form", "btn-create-tournament-modal");
    setupModal("modal-celebration");

    document.getElementById("btn-create-tournament-manual")?.addEventListener("click", () => {
        document.getElementById("form-tournament-id").value = "";
        document.getElementById("form-name").value = "";
        document.getElementById("form-player-names").value = "";
        document.getElementById("modal-tournament-form").classList.add("open");
    });

    // Template chips for AI Generator
    document.querySelectorAll(".template-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            document.getElementById("tab-ai-gen-prompt").value = chip.dataset.prompt;
        });
    });

    // Active Tournament Selector Change
    const activeSelect = document.getElementById("select-active-tournament");
    activeSelect.addEventListener("change", (e) => {
        const selectedId = e.target.value;
        if (selectedId) {
            fetchTournamentDetails(selectedId);
        }
    });

    // API Calls
    async function loadTournamentsList() {
        try {
            const res = await fetch("/api/tournaments");
            tournamentsList = await res.json();
            
            activeSelect.innerHTML = '<option value="">-- Select a Tournament --</option>';
            tournamentsList.forEach(t => {
                const opt = document.createElement("option");
                opt.value = t.id;
                opt.textContent = `${t.name} (${t.match_type})`;
                if (currentTournament && currentTournament.id === t.id) opt.selected = true;
                activeSelect.appendChild(opt);
            });

            const container = document.getElementById("tournaments-list-container");
            if (!container) return;
            container.innerHTML = "";

            if (tournamentsList.length === 0) {
                container.innerHTML = '<p class="empty-state">No tournaments created yet. Use "✨ AI Studio" to generate a tournament!</p>';
                return;
            }

            tournamentsList.forEach(t => {
                const card = document.createElement("div");
                card.className = "glass-card";
                card.style.display = "flex";
                card.style.flexDirection = "column";
                card.style.gap = "12px";
                card.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div>
                            <span class="badge badge-type">${t.match_type}</span>
                            <h3 style="margin-top:6px; font-size:1.2rem;">${t.name}</h3>
                        </div>
                        <span class="badge badge-status">${t.status}</span>
                    </div>
                    <p style="font-size:0.85rem; color:var(--text-muted);">
                        📍 ${t.venue || "No venue"} | 👥 ${t.num_players} Players | 🏟️ ${t.num_courts} Courts | 🎯 Target: ${t.target_score} pts
                    </p>
                    <div style="font-size:0.8rem; color:var(--text-dim); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                        👥 Players: ${t.players ? t.players.join(", ") : "Default"}
                    </div>
                    <div style="display:flex; gap:8px; margin-top:8px;">
                        <button class="btn btn-secondary btn-select-t" data-id="${t.id}">Select</button>
                        <button class="btn btn-danger btn-delete-t" data-id="${t.id}">Delete</button>
                    </div>
                `;
                container.appendChild(card);
            });

            container.querySelectorAll(".btn-select-t").forEach(b => {
                b.addEventListener("click", () => fetchTournamentDetails(b.dataset.id));
            });

            container.querySelectorAll(".btn-delete-t").forEach(b => {
                b.addEventListener("click", () => deleteTournament(b.dataset.id));
            });

            if (!currentTournament && tournamentsList.length > 0) {
                fetchTournamentDetails(tournamentsList[0].id);
            }
        } catch (err) {
            console.error("Error loading tournaments list:", err);
        }
    }

    async function fetchTournamentDetails(id) {
        try {
            const res = await fetch(`/api/tournaments/${id}`);
            currentTournament = await res.json();
            activeSelect.value = id;
            updateDashboardView();
            renderMatches();
            renderLeaderboard();
        } catch (err) {
            console.error("Error fetching tournament details:", err);
        }
    }

    async function updateDashboardView() {
        if (!currentTournament) return;
        const res = await fetch(`/api/tournaments/${currentTournament.id}/dashboard`);
        const dash = await res.json();

        document.getElementById("dash-title").textContent = dash.name;
        document.getElementById("dash-match-type").textContent = dash.match_type;
        document.getElementById("dash-status").textContent = dash.status;
        document.getElementById("dash-venue").textContent = dash.venue || "TBD";
        document.getElementById("dash-datetime").textContent = `${dash.date || "TBD"} ${dash.time || ""}`;
        document.getElementById("dash-target-score").textContent = `${dash.target_score} pts`;

        document.getElementById("dash-players").textContent = dash.num_players;
        document.getElementById("dash-courts").textContent = dash.num_courts;
        document.getElementById("dash-round").textContent = dash.current_round;
        document.getElementById("dash-leader").textContent = dash.current_leader;

        document.getElementById("dash-completed-matches").textContent = dash.completed_matches;
        document.getElementById("dash-remaining-matches").textContent = dash.remaining_matches;
        document.getElementById("dash-total-matches").textContent = dash.total_matches;
        
        const pct = dash.completion_percentage;
        document.getElementById("dash-progress-text").textContent = `${pct}%`;
        const circle = document.getElementById("dash-progress-circle");
        if (circle) {
            const circumference = 314.15;
            const offset = circumference - (pct / 100) * circumference;
            circle.style.strokeDashoffset = offset;
        }

        if (dash.status === "Completed" && pct === 100) {
            showCelebrationModal();
        }
    }

    // Render Matches List
    function renderMatches() {
        const container = document.getElementById("matches-container");
        const pillsContainer = document.getElementById("round-pills-container");
        const btnMexicanoNext = document.getElementById("btn-mexicano-next-round");

        if (!currentTournament || !currentTournament.matches || currentTournament.matches.length === 0) {
            container.innerHTML = '<p class="empty-state">No matches generated yet. Click "⚡ Generate Matches" above to schedule rounds!</p>';
            if (btnMexicanoNext) btnMexicanoNext.classList.add("hidden");
            return;
        }

        if (currentTournament.match_type === "Mexicano") {
            btnMexicanoNext.classList.remove("hidden");
        } else {
            btnMexicanoNext.classList.add("hidden");
        }

        const rounds = [...new Set(currentTournament.matches.map(m => m.round))];
        pillsContainer.innerHTML = '<button class="pill active" data-round="all">All Rounds</button>';
        rounds.forEach(r => {
            pillsContainer.innerHTML += `<button class="pill" data-round="${r}">Round ${r}</button>`;
        });

        pillsContainer.querySelectorAll(".pill").forEach(p => {
            p.addEventListener("click", () => {
                pillsContainer.querySelectorAll(".pill").forEach(b => b.classList.remove("active"));
                p.classList.add("active");
                filterMatches(p.dataset.round);
            });
        });

        filterMatches("all");
    }

    function filterMatches(roundFilter) {
        const container = document.getElementById("matches-container");
        container.innerHTML = "";

        const matches = currentTournament.matches.filter(m => {
            return roundFilter === "all" || m.round.toString() === roundFilter.toString();
        });

        matches.forEach(m => {
            const card = document.createElement("div");
            card.className = `match-card ${m.status.toLowerCase()}`;
            card.innerHTML = `
                <div class="match-header">
                    <span class="court-badge">Round ${m.round} • ${m.court}</span>
                    <span class="badge ${m.status === "Finished" ? "badge-status" : "badge-type"}">${m.status}</span>
                </div>
                <div class="match-body">
                    <div class="team-box">
                        <span class="team-players">${m.team_a.join("<br>& ")}</span>
                        <div class="score-control">
                            <button class="btn-score btn-score-dec" data-id="${m.id}" data-team="a">-</button>
                            <span class="score-display">${m.score_a}</span>
                            <button class="btn-score btn-score-inc" data-id="${m.id}" data-team="a">+</button>
                        </div>
                    </div>
                    <span class="vs-divider">VS</span>
                    <div class="team-box">
                        <span class="team-players">${m.team_b.join("<br>& ")}</span>
                        <div class="score-control">
                            <button class="btn-score btn-score-dec" data-id="${m.id}" data-team="b">-</button>
                            <span class="score-display">${m.score_b}</span>
                            <button class="btn-score btn-score-inc" data-id="${m.id}" data-team="b">+</button>
                        </div>
                    </div>
                </div>
            `;
            container.appendChild(card);
        });

        container.querySelectorAll(".btn-score").forEach(b => {
            b.addEventListener("click", () => {
                const matchId = b.dataset.id;
                const team = b.dataset.team;
                const isInc = b.classList.contains("btn-score-inc");
                const match = currentTournament.matches.find(m => m.id === matchId);
                if (!match) return;

                let newA = match.score_a;
                let newB = match.score_b;

                if (team === "a") newA = isInc ? newA + 1 : Math.max(0, newA - 1);
                if (team === "b") newB = isInc ? newB + 1 : Math.max(0, newB - 1);

                // Front-end Score Total Limit Validation (Max 21 pts)
                const maxTarget = currentTournament.target_score > 0 ? Math.min(21, currentTournament.target_score) : 21;
                if ((newA + newB) > maxTarget) {
                    alert(`Total match score (${newA + newB}) cannot be more than ${maxTarget} points.`);
                    return;
                }

                updateMatchScore(matchId, newA, newB);
            });
        });
    }

    async function updateMatchScore(matchId, scoreA, scoreB) {
        if (!currentTournament) return;
        try {
            const res = await fetch(`/api/tournaments/${currentTournament.id}/matches/${matchId}/score`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ score_a: scoreA, score_b: scoreB })
            });
            if (res.ok) {
                fetchTournamentDetails(currentTournament.id);
            } else {
                const errData = await res.json();
                alert(errData.detail || "Error updating match score.");
            }
        } catch (err) {
            console.error("Error updating match score:", err);
        }
    }

    // Render Leaderboard
    async function renderLeaderboard() {
        if (!currentTournament) return;
        try {
            const res = await fetch(`/api/tournaments/${currentTournament.id}/leaderboard`);
            const leaderboard = await res.json();

            const tbody = document.getElementById("leaderboard-tbody");
            tbody.innerHTML = "";

            if (!leaderboard || leaderboard.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No rankings calculated yet.</td></tr>';
                return;
            }

            leaderboard.forEach(p => {
                const tr = document.createElement("tr");
                let rankClass = "rank-badge";
                if (p.rank === 1) rankClass += " rank-1";
                if (p.rank === 2) rankClass += " rank-2";
                if (p.rank === 3) rankClass += " rank-3";

                tr.innerHTML = `
                    <td><span class="${rankClass}">${p.rank === 1 ? '🥇' : p.rank === 2 ? '🥈' : p.rank === 3 ? '🥉' : p.rank}</span></td>
                    <td><strong>${p.player_name}</strong></td>
                    <td style="font-family:var(--font-display); font-weight:700; color:var(--primary);">${p.total_points} pts</td>
                    <td style="color:var(--success); font-weight:600;">${p.wins}</td>
                    <td style="color:var(--danger); font-weight:600;">${p.losses}</td>
                    <td style="font-weight:600;">${p.point_difference > 0 ? '+' + p.point_difference : p.point_difference}</td>
                    <td>${p.matches_played}</td>
                `;
                tbody.appendChild(tr);
            });

            const top3List = document.getElementById("dash-top3-list");
            if (top3List) {
                top3List.innerHTML = "";
                leaderboard.slice(0, 3).forEach(p => {
                    const item = document.createElement("div");
                    item.style.display = "flex";
                    item.style.justifyContent = "space-between";
                    item.style.alignItems = "center";
                    item.style.padding = "8px 0";
                    item.style.borderBottom = "1px solid var(--border-color)";
                    item.innerHTML = `
                        <span>${p.rank === 1 ? '🥇' : p.rank === 2 ? '🥈' : '🥉'} <strong>${p.player_name}</strong></span>
                        <strong style="color:var(--primary);">${p.total_points} pts</strong>
                    `;
                    top3List.appendChild(item);
                });
            }
        } catch (err) {
            console.error("Error fetching leaderboard:", err);
        }
    }

    // AI Studio: Run Tournament Generator (Multi-Turn Challenge for Missing Details like Venue)
    async function runAiGenerator(promptText) {
        originalPromptText = promptText;
        const loader = document.getElementById("tab-ai-gen-loader");
        const challengeCard = document.getElementById("tab-ai-challenge-card");
        const resultCard = document.getElementById("tab-ai-gen-result");

        loader.classList.remove("hidden");
        challengeCard.classList.add("hidden");
        resultCard.classList.add("hidden");

        try {
            const res = await fetch("/api/ai/generate-tournament", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ prompt: promptText })
            });
            const data = await res.json();
            currentAiGeneratedSpec = data;

            // Check if Gemma requests more info (e.g. missing venue)
            if (data.status === "needs_info") {
                document.getElementById("challenge-message-text").textContent = data.challenge_message || "Please provide the missing details to create the tournament.";
                document.getElementById("challenge-reply-input").value = "";
                
                const tagsContainer = document.getElementById("challenge-missing-tags");
                tagsContainer.innerHTML = "";
                if (data.missing_fields && data.missing_fields.length > 0) {
                    data.missing_fields.forEach(field => {
                        const tag = document.createElement("span");
                        tag.className = "missing-tag";
                        tag.textContent = `⚠️ Required: ${field.replace("_", " ")}`;
                        tagsContainer.appendChild(tag);
                    });
                }
                challengeCard.classList.remove("hidden");
            } else {
                // Info is complete
                document.getElementById("res-title").textContent = data.tournament_name || "Padel Tournament";
                document.getElementById("res-type").textContent = data.match_type || "Americano";
                document.getElementById("res-players").textContent = data.num_players || 8;
                document.getElementById("res-courts").textContent = data.num_courts || 2;
                document.getElementById("res-target").textContent = `${data.target_score || 21} pts`;
                document.getElementById("res-datetime").textContent = `${data.date || "TBD"} ${data.time || ""}`;
                document.getElementById("res-venue").textContent = data.venue || "TBD";

                const playerNamesTextarea = document.getElementById("res-player-names-textarea");
                if (data.player_names && data.player_names.length > 0) {
                    playerNamesTextarea.value = data.player_names.join(", ");
                } else {
                    const defaultNames = [];
                    const numP = data.num_players || 8;
                    for (let i = 1; i <= numP; i++) defaultNames.push(`Player ${i}`);
                    playerNamesTextarea.value = defaultNames.join(", ");
                }

                resultCard.classList.remove("hidden");
            }
        } catch (err) {
            console.error("Error running AI generator:", err);
        } finally {
            loader.classList.add("hidden");
        }
    }

    document.getElementById("btn-tab-run-gen")?.addEventListener("click", () => {
        const prompt = document.getElementById("tab-ai-gen-prompt").value;
        if (prompt) runAiGenerator(prompt);
    });

    // Handle Challenge Reply Submission (Continues Multi-Turn Challenge until ALL fields provided)
    document.getElementById("btn-submit-challenge-reply")?.addEventListener("click", () => {
        const reply = document.getElementById("challenge-reply-input").value;
        if (!reply) return;
        const combinedPrompt = `${originalPromptText}. Additional details: ${reply}`;
        document.getElementById("tab-ai-gen-prompt").value = combinedPrompt;
        runAiGenerator(combinedPrompt);
    });

    // AI Studio: Launch Generated Tournament
    document.getElementById("btn-launch-ai-tournament")?.addEventListener("click", async () => {
        if (!currentAiGeneratedSpec) return;

        const rawPlayerNames = document.getElementById("res-player-names-textarea").value;
        const parsedPlayers = rawPlayerNames
            .split(/[\n,]+/)
            .map(p => p.trim())
            .filter(p => p.length > 0);

        const payload = {
            name: currentAiGeneratedSpec.tournament_name || "Padel Tournament",
            match_type: currentAiGeneratedSpec.match_type || "Americano",
            num_players: parsedPlayers.length > 0 ? parsedPlayers.length : (currentAiGeneratedSpec.num_players || 8),
            num_courts: currentAiGeneratedSpec.num_courts || 2,
            target_score: currentAiGeneratedSpec.target_score || 21,
            date: currentAiGeneratedSpec.date || "",
            time: currentAiGeneratedSpec.time || "",
            venue: currentAiGeneratedSpec.venue || "",
            players: parsedPlayers,
        };

        try {
            const res = await fetch("/api/tournaments", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const newT = await res.json();
            
            await fetch(`/api/tournaments/${newT.id}/generate-matches`, { method: "POST" });
            
            loadTournamentsList();
            fetchTournamentDetails(newT.id);
            switchTab("dashboard");
        } catch (err) {
            console.error("Error launching tournament:", err);
        }
    });

    // AI Studio: Run Venue Finder
    document.getElementById("btn-tab-run-venue")?.addEventListener("click", async () => {
        const prompt = document.getElementById("tab-ai-venue-prompt").value;
        if (!prompt) return;

        const loader = document.getElementById("tab-ai-venue-loader");
        const container = document.getElementById("tab-venue-results-container");
        loader.classList.remove("hidden");
        container.innerHTML = "";

        try {
            const res = await fetch("/api/ai/recommend-venues", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ prompt })
            });
            const venues = await res.json();

            venues.forEach(v => {
                const item = document.createElement("div");
                item.className = "venue-card-item";
                item.innerHTML = `
                    <div>
                        <h4>${v.venue_name}</h4>
                        <p>📍 ${v.address} • 🏟️ ${v.courts} courts</p>
                        <p style="font-size:0.75rem; color:var(--text-dim); margin-top:2px;">${v.description}</p>
                    </div>
                    <button class="btn btn-secondary btn-use-venue-tab" data-name="${v.venue_name}" data-courts="${v.courts}">➕ Select Venue</button>
                `;
                container.appendChild(item);
            });

            container.querySelectorAll(".btn-use-venue-tab").forEach(b => {
                b.addEventListener("click", () => {
                    const venueName = b.dataset.name;
                    const courts = b.dataset.courts;
                    document.getElementById("tab-ai-gen-prompt").value = `Create an Americano tournament for 8 players at ${venueName} with ${courts} courts.`;
                });
            });
        } catch (err) {
            console.error("Error fetching AI venue recommendations:", err);
        } finally {
            loader.classList.add("hidden");
        }
    });

    // AI Studio: Ask Gemma Chat Advisor
    document.getElementById("btn-send-ai-chat")?.addEventListener("click", async () => {
        const input = document.getElementById("ai-chat-input");
        const msg = input.value;
        if (!msg) return;

        const resBox = document.getElementById("ai-chat-response");
        resBox.textContent = "Thinking...";
        resBox.classList.remove("hidden");

        try {
            const res = await fetch("/api/ai/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: msg })
            });
            const data = await res.json();
            resBox.textContent = data.reply;
        } catch (err) {
            console.error("Error asking Gemma chat:", err);
            resBox.textContent = "Error communicating with AI advisor.";
        }
    });

    // Save / Create Tournament Manually
    document.getElementById("btn-save-tournament").addEventListener("click", async () => {
        const id = document.getElementById("form-tournament-id").value;
        const rawPlayerNames = document.getElementById("form-player-names").value;
        const parsedPlayers = rawPlayerNames
            .split(/[\n,]+/)
            .map(p => p.trim())
            .filter(p => p.length > 0);

        const numPlayersInput = parseInt(document.getElementById("form-players").value) || 8;
        const finalNumPlayers = parsedPlayers.length > 0 ? parsedPlayers.length : numPlayersInput;

        const payload = {
            name: document.getElementById("form-name").value,
            match_type: document.getElementById("form-type").value,
            num_players: finalNumPlayers,
            num_courts: parseInt(document.getElementById("form-courts").value) || 2,
            target_score: Math.min(21, parseInt(document.getElementById("form-target-score").value) || 21),
            date: document.getElementById("form-date").value,
            time: document.getElementById("form-time").value,
            venue: document.getElementById("form-venue").value,
            players: parsedPlayers.length > 0 ? parsedPlayers : null,
        };

        try {
            const url = id ? `/api/tournaments/${id}` : "/api/tournaments";
            const method = id ? "PUT" : "POST";
            const res = await fetch(url, {
                method: method,
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            document.getElementById("modal-tournament-form").classList.remove("open");
            loadTournamentsList();
            if (data.id) fetchTournamentDetails(data.id);
        } catch (err) {
            console.error("Error saving tournament:", err);
        }
    });

    // Delete Tournament
    async function deleteTournament(id) {
        if (!confirm("Are you sure you want to delete this tournament?")) return;
        try {
            await fetch(`/api/tournaments/${id}`, { method: "DELETE" });
            if (currentTournament && currentTournament.id === id) currentTournament = null;
            loadTournamentsList();
        } catch (err) {
            console.error("Error deleting tournament:", err);
        }
    }

    // Generate Matches
    document.getElementById("btn-generate-matches")?.addEventListener("click", async () => {
        if (!currentTournament) return;
        try {
            const res = await fetch(`/api/tournaments/${currentTournament.id}/generate-matches`, { method: "POST" });
            if (res.ok) fetchTournamentDetails(currentTournament.id);
        } catch (err) {
            console.error("Error generating matches:", err);
        }
    });

    // Generate Next Round (Mexicano)
    document.getElementById("btn-mexicano-next-round")?.addEventListener("click", async () => {
        if (!currentTournament) return;
        try {
            const res = await fetch(`/api/tournaments/${currentTournament.id}/next-round`, { method: "POST" });
            if (res.ok) fetchTournamentDetails(currentTournament.id);
        } catch (err) {
            console.error("Error generating Mexicano next round:", err);
        }
    });

    function showCelebrationModal() {
        const celeb = document.getElementById("modal-celebration");
        if (!celeb) return;
        document.getElementById("celeb-tournament-name").textContent = currentTournament.name;
        
        const podiumContainer = document.getElementById("celeb-podium");
        podiumContainer.innerHTML = "";
        const top3 = currentTournament.leaderboard.slice(0, 3);

        top3.forEach(p => {
            const div = document.createElement("div");
            div.style.padding = "10px";
            div.innerHTML = `
                <div style="font-size:2rem;">${p.rank === 1 ? '🥇' : p.rank === 2 ? '🥈' : '🥉'}</div>
                <strong>${p.player_name}</strong>
                <p style="color:var(--primary); font-weight:700;">${p.total_points} pts</p>
            `;
            podiumContainer.appendChild(div);
        });

        celeb.classList.add("open");
    }

    // Initial load
    loadTournamentsList();
});
