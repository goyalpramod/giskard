package ai.giskard.web.dto;

import com.dataiku.j2ts.annotations.UIModel;
import com.dataiku.j2ts.annotations.UINullable;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@NoArgsConstructor
@UIModel
public class TestSuiteCreateDTO {
    private Long projectId;
    @UINullable
    private String referenceDatasetId;
    @UINullable
    private String actualDatasetId;
    private String modelId;
    private String name;
    private boolean shouldGenerateTests;
}