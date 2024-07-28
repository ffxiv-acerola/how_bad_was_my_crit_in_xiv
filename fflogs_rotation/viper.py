from fflogs_rotation.base import BuffQuery, disjunction


class ViperActions(BuffQuery):
    def __init__(
        self,
        headers: dict,
        report_id: str,
        fight_id: int,
        player_id: int,
        flankstung_venom_id: int = 1003645,
        flanksbane_venom_id: int = 1003646,
        hindstung_venom_id: int = 1003647,
        hindsbane_venom_id: int = 1003648,
        hunters_venom_id: int = 1003657,
        swiftskins_venom_id: int = 1003658,
        poised_twinfang_id: int = 1003665,
        poised_twinblood_id: int = 1003666,
    ) -> None:
        self.report_id = report_id
        self.fight_id = fight_id
        self.player_id = player_id

        # Single target buff IDs
        self.flankstung_venom_id = flankstung_venom_id
        self.flanksbane_venom_id = flanksbane_venom_id
        self.hindstung_venom_id = hindstung_venom_id
        self.hindsbane_venom_id = hindsbane_venom_id
        self.hunters_venom_id = hunters_venom_id
        self.swiftskins_venom_id = swiftskins_venom_id
        self.poised_twinfang_id = poised_twinfang_id
        self.poised_twinblood_id = poised_twinblood_id

        # AoE buff IDs
        self.fellskins_venom_id = 1003660
        self.fellhunters_venom_id = 1003659
        self.grimhunters_venom_id = 1003649
        self.grimskins_venom_id = 1003650

        self.buff_action_map = {
            self.flankstung_venom_id: 34610,
            self.flanksbane_venom_id: 34610,
            self.hindstung_venom_id: 34612,
            self.hindsbane_venom_id: 34613,
            self.hunters_venom_id: 34636,
            self.swiftskins_venom_id: 34637,
            self.poised_twinfang_id: 34644,
            self.poised_twinblood_id: 34645,
            self.fellskins_venom_id: 34639,
            self.fellhunters_venom_id: 34638,
            self.grimhunters_venom_id: 34618,
            self.grimskins_venom_id: 34619,
        }

        # Used to check Nth generation combo was performed.
        self.viper_weaponskills = {
            34606,
            34608,
            34607,
            34632,
            34617,
            34614,
            34609,
            34610,
            34611,
            34612,
            34613,
            34615,
            34616,
            34617,
            34618,
            34619,
            34620,
            34621,
            34622,
            34623,
            34624,
            34625,
            34633,
            34626,
            34627,
            34628,
            34629,
            34630,
            34631,
        }

        self.generation_combo_piror_combo_ids = {
            34627: 34626,
            34628: 34627,
            34629: 34628,
            34630: 34629,
        }

        self.set_viper_buff_times(headers)
        pass

    def set_viper_buff_times(self, headers):
        """Set buffs so corresponding actions have their potency increased.
        By Buff -> Action potency increase:
        - Flankesbane Venom -> Flanksbane Fang
        - Flankstung Venom -> Flanksting Strike
        - Hindsbane Venom -> Hindsbane Fang
        - Hindstung Venom -> Hindsting Strike
        - Swiftskin's Venom -> Twinblood Bite
        - Hunter's Venom -> Twinfang Bite
        - Poised for Twinfang -> Uncoiled Twinfang
        - Poised for Twinblood -> Uncoiled Twinblood
        """

        # TODO: Can remove flanks/hinds buffs.
        query = """
        query ViperBuffs(
            $code: String!
            $id: [Int]!
            $playerID: Int!
            $flankstungID: Float!
            $flanksbaneID: Float!
            $hindstungID: Float!
            $hindsbaneID: Float!
            $huntersID: Float!
            $swiftskinsID: Float!
            $poisedTwinfangID: Float!
            $poisedTwinbloodID: Float!
            $fellskinsID: Float!
            $fellhuntersID: Float!
            $grimhuntersID: Float!
            $grimskinsID: Float!
        ) {
            reportData {
                report(code: $code) {
                    startTime
                    flankstung: table(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $flankstungID
                    )
                    flanksbane: table(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $flanksbaneID
                    )
                    hindstung: table(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $hindstungID
                    )
                    hindsbane: table(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $hindsbaneID
                    )
                    hunters: table(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $huntersID
                    )
                    swiftskins: table(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $swiftskinsID
                    )
                    poisedTwinfang: table(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $poisedTwinfangID
                    )
                    poisedTwinblood: table(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $poisedTwinbloodID
                    )
                    fellskins: table(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $fellskinsID
                    )
                    fellhunters: table(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $fellhuntersID
                    )		
                    grimhunters: table(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $grimhuntersID
                    )		
                    grimskins: table(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $grimskinsID
                    )		
                }
            }
        }
        """

        variables = {
            "code": self.report_id,
            "id": [self.fight_id],
            "playerID": self.player_id,
            "flanksbaneID": self.flanksbane_venom_id,
            "flankstungID": self.flankstung_venom_id,
            "hindstungID": self.hindstung_venom_id,
            "hindsbaneID": self.hindsbane_venom_id,
            "huntersID": self.hunters_venom_id,
            "swiftskinsID": self.swiftskins_venom_id,
            "poisedTwinfangID": self.poised_twinfang_id,
            "poisedTwinbloodID": self.poised_twinblood_id,
            "fellskinsID": self.fellskins_venom_id,
            "fellhuntersID": self.fellhunters_venom_id,
            "grimhuntersID": self.grimhunters_venom_id,
            "grimskinsID": self.grimskins_venom_id,
        }

        self._perform_graph_ql_query(headers, query, variables, "ViperBuffs")

        self.flanksbane_venom_times = self._get_buff_times("flanksbane")
        self.flankstung_venom_times = self._get_buff_times("flankstung")
        self.hindstung_venom_times = self._get_buff_times("hindstung")
        self.hindsbane_venom_times = self._get_buff_times("hindsbane")
        self.hunters_venom_times = self._get_buff_times("hunters")
        self.swiftskins_venom_times = self._get_buff_times("swiftskins")
        self.poised_twinfang_times = self._get_buff_times("poisedTwinfang")
        self.poised_twinblood_times = self._get_buff_times("poisedTwinblood")
        self.fellskins_venom_times = self._get_buff_times("fellskins")
        self.fellhunters_venom_times = self._get_buff_times("fellhunters")
        self.grimhunters_venom_times = self._get_buff_times("grimhunters")
        self.grimskins_venom_times = self._get_buff_times("grimskins")
        pass

    def _apply_generation_combo_chains(self, actions_df):
        """Check if Nth Generation followed the correct combo chain and apply a buff so
        the correct potency is applied.

        - Reawaken -> First Generation
        - First Generation -> Second Generation
        - Second Generation -> Third Generation
        - Third Generation -> Fourth Generation
        """
        # Filter to just weaponskills
        weaponskill_df = actions_df[
            actions_df["abilityGameID"].isin(self.viper_weaponskills)
        ][["abilityGameID", "action_name", "buffs"]].copy()

        weaponskill_df["priorWeaponskillID"] = weaponskill_df["abilityGameID"].shift(1)

        # Apply conditions for all the combo chans
        generation_combo_chains = list(
            (weaponskill_df["abilityGameID"] == combo)
            & (weaponskill_df["priorWeaponskillID"] == prior)
            for combo, prior in self.generation_combo_piror_combo_ids.items()
        )

        generation_combo_condition = disjunction(*generation_combo_chains)

        # Apply buffs for satisfied combo chains
        weaponskill_df = self._apply_buffs(
            weaponskill_df, generation_combo_condition, "combo"
        )

        # Just get new action name and buff list
        weaponskill_df = weaponskill_df[
            weaponskill_df["abilityGameID"].isin(
                self.generation_combo_piror_combo_ids.keys()
            )
        ][["action_name", "buffs"]]

        # Update original values in the actions DF
        actions_df.loc[
            actions_df["abilityGameID"].isin(
                self.generation_combo_piror_combo_ids.keys()
            ),
            ["action_name", "buffs"],
        ] = weaponskill_df

        return actions_df

    def apply_viper_buffs(self, actions_df):
        actions_df = self._apply_generation_combo_chains(actions_df)

        # Loop through and apply all the buffs to each action
        for k, times in {
            self.flanksbane_venom_id: self.flanksbane_venom_times,
            self.flankstung_venom_id: self.flankstung_venom_times,
            self.hindsbane_venom_id: self.hindsbane_venom_times,
            self.hindstung_venom_id: self.hindstung_venom_times,
            self.swiftskins_venom_id: self.swiftskins_venom_times,
            self.hunters_venom_id: self.hunters_venom_times,
            self.poised_twinblood_id: self.poised_twinblood_times,
            self.poised_twinfang_id: self.poised_twinblood_times,
            self.fellhunters_venom_id: self.fellhunters_venom_times,
            self.fellskins_venom_id: self.fellhunters_venom_times,
            self.grimhunters_venom_id: self.grimhunters_venom_times,
            self.grimskins_venom_id: self.grimskins_venom_times,
        }.items():
            betweens = list(
                actions_df["timestamp"].between(b[0], b[1], inclusive="both")
                for b in times
            )

            condition = disjunction(*betweens) & (
                actions_df["abilityGameID"] == self.buff_action_map[k]
            )

            actions_df = self._apply_buffs(actions_df, condition, k)

        return actions_df


if __name__ == "__main__":
    from fflogs_rotation.rotation import headers

    ViperActions(headers, "ZTHC2AVM3wcxXhKz", 2, 7)
